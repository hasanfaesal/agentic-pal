"""
Response synthesis node.
LLM call #2: Formats tool results into natural language response.

Supports two modes:
- "legacy": Traditional LangChain with string prompts
- "dspy": DSPy signatures and modules for structured prompting
"""

from ..state import AgentState
from ..prompts.config import PromptConfig


def _synthesize_response_dspy(state: AgentState, llm) -> AgentState:
    """
    DSPy-based response synthesis using structured signatures.
    
    Args:
        state: Current agent state with results
        llm: LLM instance (used to configure DSPy if needed)
        
    Returns:
        Updated state with final_response
    """
    import json
    from ..prompts.synthesize_response import (
        ResponseHandler,
        ResponseSynthesisModule,
        ConversationalModule,
        ErrorRecoveryModule,
    )
    
    user_message = state["user_message"]
    results = state.get("results", {})
    actions = state.get("actions", [])
    confirmation_message = state.get("confirmation_message")
    error = state.get("error")
    
    # Handle confirmation message (no LLM needed)
    if confirmation_message and state.get("pending_confirmation"):
        return {**state, "final_response": confirmation_message}
    
    # Handle errors with DSPy ErrorRecoveryModule
    if error:
        try:
            error_module = ErrorRecoveryModule()
            result = error_module(
                user_request=user_message,
                error_message=str(error),
                tool_name="unknown"
            )
            return {**state, "final_response": result.response}
        except Exception:
            return {
                **state, 
                "final_response": f"I encountered an error: {error}. Please try again.",
            }
    
    # Handle no actions case (conversational response)
    if not actions:
        try:
            conv_module = ConversationalModule()
            result = conv_module(user_message=user_message)
            return {**state, "final_response": result.response}
        except Exception:
            return {**state, "final_response": "I'm here to help! What would you like me to do?"}
    
    # Build results summary for DSPy
    results_summary = []
    for action in actions:
        action_id = action["id"]
        tool = action["tool"]
        result = results.get(action_id, {})
        
        # Include the full result - different tools return data in different keys
        # (tasks, events, emails, etc.) so we pass everything
        results_summary.append({
            "tool": tool,
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "result": result,  # Pass full result for LLM to interpret
            "error": result.get("error"),
        })
    
    # Use DSPy ResponseSynthesisModule
    try:
        synth_module = ResponseSynthesisModule()
        result = synth_module(
            user_request=user_message,
            tool_results=json.dumps(results_summary, indent=2, default=str)
        )
        return {**state, "final_response": result.response}
    except Exception as e:
        # Fallback on error
        return {
            **state, 
            "final_response": f"Completed your request. Results: {json.dumps(results_summary, default=str)[:500]}",
        }


def _synthesize_response_legacy(state: AgentState, llm) -> AgentState:
    """
    Legacy response synthesis using LangChain with string prompts.
    
    Args:
        state: Current agent state with results
        llm: LLM instance
        
    Returns:
        Updated state with final_response
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    from ..prompts.synthesize_response import SYNTHESIZE_RESPONSE_PROMPT
    import json
    
    user_message = state["user_message"]
    results = state.get("results", {})
    actions = state.get("actions", [])
    confirmation_message = state.get("confirmation_message")
    error = state.get("error")
    
    # Handle confirmation message (no LLM needed)
    if confirmation_message and state.get("pending_confirmation"):
        return {**state, "final_response": confirmation_message}
    
    # Handle errors
    if error:
        return {
            **state, 
            "final_response": f"I encountered an error: {error}. Please try again.",
        }
    
    # Handle no actions case
    if not actions:
        # No tools needed - just respond conversationally
        messages = [
            SystemMessage(content="You are a helpful assistant. Respond naturally to the user."),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        return {**state, "final_response": response.content}
    
    # Build results summary for LLM
    results_summary = []
    for action in actions:
        action_id = action["id"]
        tool = action["tool"]
        result = results.get(action_id, {})
        
        # Include the full result - different tools return data in different keys
        # (tasks, events, emails, etc.) so we pass everything
        results_summary.append({
            "tool": tool,
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "result": result,  # Pass full result for LLM to interpret
            "error": result.get("error"),
        })
    
    # Call LLM to format response
    messages = [
        SystemMessage(content=SYNTHESIZE_RESPONSE_PROMPT),
        HumanMessage(content=f"""
User's original request: {user_message}

Tool execution results:
{json.dumps(results_summary, indent=2, default=str)}

Generate a natural, helpful response summarizing what was done.
If any tools failed, explain the error and suggest alternatives.
Format lists and data nicely for readability.
"""),
    ]
    
    response = llm.invoke(messages)
    
    return {**state, "final_response": response.content}


def synthesize_response(state: AgentState, llm) -> AgentState:
    """
    Synthesize final response from tool results.
    
    Routes to either DSPy or legacy implementation based on PromptConfig.
    
    This is LLM Call #2 - the response formatting call.
    
    Args:
        state: Current agent state with results
        llm: LLM instance
        
    Returns:
        Updated state with final_response
    """
    if PromptConfig.is_dspy():
        return _synthesize_response_dspy(state, llm)
    else:
        return _synthesize_response_legacy(state, llm)
