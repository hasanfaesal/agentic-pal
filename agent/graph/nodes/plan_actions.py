"""
The LLM uses three meta-tools instead of having all tool schemas loaded upfront:
1. discover_tools - Find tools by category/action
2. get_tool_schema - Get full schema for a specific tool
3. invoke_tool - Execute a tool with parameters
"""

import asyncio
import json
from typing import List, Dict, Any
from ..state import AgentState
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from ..prompts.plan_actions import PLAN_ACTIONS_SYSTEM_PROMPT
from datetime import datetime

# List of destructive tools that require confirmation
DESTRUCTIVE_TOOLS = {
    "delete_calendar_event",
    "delete_task",
}


def _parse_tool_calls_from_response(response) -> List[dict]:
    """
    Parse tool calls from LLM response.
    
    Args:
        response: LLM response object
        
    Returns:
        List of tool call dicts with name and args
    """
    tool_calls = []
    
    # Check for tool_calls in the response
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            tool_calls.append({
                "name": tc.get("name", tc.get("function", {}).get("name")),
                "args": tc.get("args", tc.get("function", {}).get("arguments", {})),
                "id": tc.get("id"),
            })
    
    return tool_calls


def plan_actions(state: AgentState, meta_tools, llm) -> AgentState:
    """
    Args:
        state: Current agent state
        meta_tools: MetaTools instance with discover/schema/invoke
        llm: LLM instance (will be bound with meta-tools)
        
    Returns:
        Updated state with actions and results
    """
    
    user_message = state["user_message"]
    conversation_history = state.get("conversation_history", [])
    
    # Build the system prompt with current date/time
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    current_time = datetime.now().strftime("%I:%M %p")
    
    system_prompt = PLAN_ACTIONS_SYSTEM_PROMPT.format(
        current_date=current_date,
        current_time=current_time,
    )
    
    # Get meta-tools for LLM binding
    tools = meta_tools.get_langchain_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    # Build initial messages
    messages = [
        SystemMessage(content=system_prompt),
    ]
    
    # Add recent conversation history
    for msg in conversation_history[-5:]:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    
    # Add current user message
    messages.append(HumanMessage(content=user_message))
    
    # Agent loop - let LLM use meta-tools until it produces a final response
    max_iterations = 10  # Prevent infinite loops
    actions = []
    results = {}
    discovered_tools = []
    requires_confirmation = False
    
    for iteration in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        
        # Check for tool calls
        tool_calls = _parse_tool_calls_from_response(response)
        
        if not tool_calls:
            # No more tool calls - LLM is done
            break
        
        # Add AI response to messages
        messages.append(response)
        
        # Execute each tool call
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc.get("id", f"tool_{iteration}")
            
            if tool_name == "discover_tools":
                result = meta_tools.discover_tools(**tool_args)
                discovered_tools.extend([t["name"] for t in result.get("tools", [])])
                
            elif tool_name == "get_tool_schema":
                result = meta_tools.get_tool_schema(**tool_args)
                
            elif tool_name == "invoke_tool":
                invoked_tool = tool_args.get("tool_name", "")
                params = tool_args.get("parameters", {})
                
                # Check if this is a destructive operation
                if invoked_tool in DESTRUCTIVE_TOOLS:
                    requires_confirmation = True
                    result = {
                        "status": "pending_confirmation",
                        "tool": invoked_tool,
                        "parameters": params,
                        "message": f"This will {invoked_tool.replace('_', ' ')}. Please confirm.",
                    }
                    actions.append({
                        "id": f"a{len(actions)+1}",
                        "tool": invoked_tool,
                        "args": params,
                        "depends_on": [],
                        "pending_confirmation": True,
                    })
                else:
                    result = meta_tools.invoke_tool(invoked_tool, params)
                    action_id = f"a{len(actions)+1}"
                    actions.append({
                        "id": action_id,
                        "tool": invoked_tool,
                        "args": params,
                        "depends_on": [],
                    })
                    results[action_id] = result
            else:
                result = {"error": f"Unknown meta-tool: {tool_name}"}
            
            # Add tool result to messages
            messages.append(ToolMessage(
                content=json.dumps(result, default=str),
                tool_call_id=tool_id,
            ))
    
    return {
        **state,
        "actions": actions,
        "results": results,
        "requires_confirmation": requires_confirmation,
        "discovered_tools": list(set(discovered_tools)),
        "tool_invocations": actions,
    }
