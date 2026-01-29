"""
Response synthesis node.
LLM call #2: Formats tool results into natural language response.
"""

from ..state import AgentState


def synthesize_response(state: AgentState, llm) -> AgentState:
    """
    Synthesize final response from tool results.
    
    This is LLM Call #2 - the response formatting call.
    
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
        
        results_summary.append({
            "tool": tool,
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "data": result.get("data", {}),
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
