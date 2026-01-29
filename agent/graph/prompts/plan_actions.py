"""
DSPy-based prompts and signatures for action planning with meta-tools.
"""

import dspy
from typing import List, Optional, Literal


class ToolDiscovery(dspy.Signature):
    """Find available tools by category and/or action type to help answer user requests."""
    
    user_request: str = dspy.InputField(desc="The user's original request")
    categories: Optional[List[str]] = dspy.InputField(
        desc="Tool categories to search: calendar, gmail, tasks"
    )
    actions: Optional[List[str]] = dspy.InputField(
        desc="Action types to search: search, create, update, delete, list, read"
    )
    relevant_tools: List[str] = dspy.OutputField(
        desc="List of tool names that are relevant to the user's request"
    )


class ToolInvocation(dspy.Signature):
    """Determine the correct tool and parameters to use for a user request."""
    
    user_request: str = dspy.InputField(desc="The user's original request")
    available_tools: List[str] = dspy.InputField(desc="Tools discovered as relevant")
    tool_schemas: str = dspy.InputField(desc="JSON schemas of available tools")
    current_date: str = dspy.InputField(desc="Current date for context")
    current_time: str = dspy.InputField(desc="Current time for context")
    
    selected_tool: str = dspy.OutputField(desc="The tool name to invoke")
    parameters: str = dspy.OutputField(desc="JSON string of parameters to pass to the tool")
    reasoning: str = dspy.OutputField(desc="Brief explanation of why this tool and parameters were chosen")


class ActionPlanner(dspy.Signature):
    """
    Plan actions to fulfill a user request using meta-tools.
    
    You are a personal productivity assistant that can manage calendar, tasks, and email.
    
    ## How to Use Tools
    
    You have 3 meta-tools to access all functionality:
    
    ### 1. discover_tools
    Find available tools by category and/or action type.
    - **Categories:** calendar, gmail, tasks
    - **Actions:** search, create, update, delete, list, read
    
    Examples:
    - Find calendar tools: discover_tools(categories=["calendar"])
    - Find tools to create things: discover_tools(actions=["create"])
    - Find email search tools: discover_tools(categories=["gmail"], actions=["search"])
    
    ### 2. get_tool_schema
    Get full parameters for a specific tool. Use this to understand required/optional parameters.
    
    ### 3. invoke_tool
    Execute a tool with the given parameters.
    
    ## Workflow
    
    1. User asks something → use discover_tools to find relevant tools
    2. For complex tools, use get_tool_schema to understand parameters
    3. Use invoke_tool to execute with the right parameters
    4. After getting results, provide a helpful response to the user
    
    ## Shortcuts (skip get_tool_schema for these simple tools)
    
    These tools have simple or no required parameters:
    - list_tasks, list_calendar_events, list_unread_emails, get_task_lists
    
    ## Important Notes
    
    - Delete operations require user confirmation
    - Date parsing: You can use natural language like "tomorrow at 2pm" or "next week"
    - Be helpful: After tool execution, summarize results in a friendly way
    """
    
    user_request: str = dspy.InputField(desc="The user's original request")
    current_date: str = dspy.InputField(desc="Current date (e.g., 'Monday, January 29, 2026')")
    current_time: str = dspy.InputField(desc="Current time (e.g., '10:30 AM')")
    conversation_history: Optional[str] = dspy.InputField(
        desc="Recent conversation history for context", default=""
    )
    
    tool_calls: str = dspy.OutputField(
        desc="JSON array of tool calls to make: [{name: str, args: dict}]"
    )
    reasoning: str = dspy.OutputField(
        desc="Step-by-step reasoning for the planned actions"
    )


class MultiStepPlanner(dspy.Signature):
    """
    Plan multi-step actions when a single tool call isn't sufficient.
    Break down complex requests into sequential or parallel tool invocations.
    """
    
    user_request: str = dspy.InputField(desc="The user's original request")
    current_date: str = dspy.InputField(desc="Current date for context")
    current_time: str = dspy.InputField(desc="Current time for context")
    previous_results: str = dspy.InputField(desc="Results from previous tool calls (if any)")
    available_tools: List[str] = dspy.InputField(desc="Available tool names")
    
    next_steps: str = dspy.OutputField(
        desc="JSON array of next tool calls: [{name: str, args: dict, depends_on: str?}]"
    )
    is_complete: bool = dspy.OutputField(
        desc="True if the user's request has been fully addressed"
    )
    reasoning: str = dspy.OutputField(desc="Explanation of the next steps planned")


# --- DSPy Modules ---

class ActionPlannerModule(dspy.Module):
    """
    DSPy module for planning actions using meta-tools.
    Uses Chain of Thought for better reasoning.
    """
    
    def __init__(self):
        super().__init__()
        self.planner = dspy.ChainOfThought(ActionPlanner)
    
    def forward(
        self, 
        user_request: str, 
        current_date: str, 
        current_time: str,
        conversation_history: str = ""
    ):
        return self.planner(
            user_request=user_request,
            current_date=current_date,
            current_time=current_time,
            conversation_history=conversation_history
        )


class ToolDiscoveryModule(dspy.Module):
    """
    DSPy module for discovering relevant tools.
    """
    
    def __init__(self):
        super().__init__()
        self.discover = dspy.Predict(ToolDiscovery)
    
    def forward(
        self, 
        user_request: str,
        categories: Optional[List[str]] = None,
        actions: Optional[List[str]] = None
    ):
        return self.discover(
            user_request=user_request,
            categories=categories,
            actions=actions
        )


class ToolInvocationModule(dspy.Module):
    """
    DSPy module for determining tool invocation parameters.
    Uses Chain of Thought for complex parameter inference.
    """
    
    def __init__(self):
        super().__init__()
        self.invoke = dspy.ChainOfThought(ToolInvocation)
    
    def forward(
        self,
        user_request: str,
        available_tools: List[str],
        tool_schemas: str,
        current_date: str,
        current_time: str
    ):
        return self.invoke(
            user_request=user_request,
            available_tools=available_tools,
            tool_schemas=tool_schemas,
            current_date=current_date,
            current_time=current_time
        )


class MultiStepPlannerModule(dspy.Module):
    """
    DSPy module for planning multi-step actions.
    """
    
    def __init__(self):
        super().__init__()
        self.planner = dspy.ChainOfThought(MultiStepPlanner)
    
    def forward(
        self,
        user_request: str,
        current_date: str,
        current_time: str,
        previous_results: str,
        available_tools: List[str]
    ):
        return self.planner(
            user_request=user_request,
            current_date=current_date,
            current_time=current_time,
            previous_results=previous_results,
            available_tools=available_tools
        )


# --- Legacy Support (for backwards compatibility) ---

def get_plan_actions_system_prompt(current_date: str, current_time: str) -> str:
    """
    Generate the system prompt for action planning.
    This function provides backwards compatibility with the existing codebase.
    
    Args:
        current_date: Current date string
        current_time: Current time string
        
    Returns:
        Formatted system prompt string
    """
    return f"""You are a personal productivity assistant that can manage calendar, tasks, and email.

**Current Date & Time:** {current_date} at {current_time}

## How to Use Tools

You have 3 meta-tools to access all functionality:

### 1. discover_tools
Find available tools by category and/or action type.
- **Categories:** calendar, gmail, tasks
- **Actions:** search, create, update, delete, list, read

Examples:
- Find calendar tools: `discover_tools(categories=["calendar"])`
- Find tools to create things: `discover_tools(actions=["create"])`
- Find email search tools: `discover_tools(categories=["gmail"], actions=["search"])`

### 2. get_tool_schema
Get full parameters for a specific tool. Use this to understand required/optional parameters.

Example: `get_tool_schema(tool_name="add_calendar_event")`

### 3. invoke_tool
Execute a tool with the given parameters.

Example: `invoke_tool(tool_name="list_tasks", parameters={{}})`

## Workflow

1. User asks something → use `discover_tools` to find relevant tools
2. For complex tools, use `get_tool_schema` to understand parameters
3. Use `invoke_tool` to execute with the right parameters
4. After getting results, provide a helpful response to the user

## Shortcuts (skip get_tool_schema for these simple tools)

These tools have simple or no required parameters:
- `invoke_tool(tool_name="list_tasks", parameters={{}})`
- `invoke_tool(tool_name="list_calendar_events", parameters={{}})`
- `invoke_tool(tool_name="list_unread_emails", parameters={{}})`
- `invoke_tool(tool_name="get_task_lists", parameters={{}})`

## Important Notes

- **Delete operations** require user confirmation - don't worry, the system handles this
- **Date parsing**: You can use natural language like "tomorrow at 2pm" or "next week"
- **Be helpful**: After tool execution, summarize results in a friendly way

## Example Flow

User: "What's on my calendar tomorrow?"

1. `discover_tools(categories=["calendar"], actions=["list"])`
   → Found: list_calendar_events

2. `invoke_tool(tool_name="list_calendar_events", parameters={{"time_min": "tomorrow", "time_max": "tomorrow"}})`
   → Returns calendar events

3. Respond: "Here's what you have scheduled for tomorrow: ..."
"""


# Keep the original constant for backwards compatibility
PLAN_ACTIONS_SYSTEM_PROMPT = """You are a personal productivity assistant that can manage calendar, tasks, and email.

**Current Date & Time:** {current_date} at {current_time}

## How to Use Tools

You have 3 meta-tools to access all functionality:

### 1. discover_tools
Find available tools by category and/or action type.
- **Categories:** calendar, gmail, tasks
- **Actions:** search, create, update, delete, list, read

Examples:
- Find calendar tools: `discover_tools(categories=["calendar"])`
- Find tools to create things: `discover_tools(actions=["create"])`
- Find email search tools: `discover_tools(categories=["gmail"], actions=["search"])`

### 2. get_tool_schema
Get full parameters for a specific tool. Use this to understand required/optional parameters.

Example: `get_tool_schema(tool_name="add_calendar_event")`

### 3. invoke_tool
Execute a tool with the given parameters.

Example: `invoke_tool(tool_name="list_tasks", parameters={{}})`

## Workflow

1. User asks something → use `discover_tools` to find relevant tools
2. For complex tools, use `get_tool_schema` to understand parameters
3. Use `invoke_tool` to execute with the right parameters
4. After getting results, provide a helpful response to the user

## Shortcuts (skip get_tool_schema for these simple tools)

These tools have simple or no required parameters:
- `invoke_tool(tool_name="list_tasks", parameters={{}})`
- `invoke_tool(tool_name="list_calendar_events", parameters={{}})`
- `invoke_tool(tool_name="list_unread_emails", parameters={{}})`
- `invoke_tool(tool_name="get_task_lists", parameters={{}})`

## Important Notes

- **Delete operations** require user confirmation - don't worry, the system handles this
- **Date parsing**: You can use natural language like "tomorrow at 2pm" or "next week"
- **Be helpful**: After tool execution, summarize results in a friendly way

## Example Flow

User: "What's on my calendar tomorrow?"

1. `discover_tools(categories=["calendar"], actions=["list"])`
   → Found: list_calendar_events

2. `invoke_tool(tool_name="list_calendar_events", parameters={{"time_min": "tomorrow", "time_max": "tomorrow"}})`
   → Returns calendar events

3. Respond: "Here's what you have scheduled for tomorrow: ..."
"""
