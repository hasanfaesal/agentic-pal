"""
Meta-tools for lazy tool loading.

This module implements the three meta-tools pattern that enables dynamic tool discovery:
1. discover_tools - Find tools by category/action/keyword
2. get_tool_schema - Get full parameter schema for a specific tool
3. invoke_tool - Execute any tool by name with parameters

This reduces tool token usage by ~96% compared to loading all tools upfront.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from .tool_index import discover_tools as _discover_tools, TOOL_INDEX


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models for Meta-Tool Parameters
# ─────────────────────────────────────────────────────────────────────────────

class DiscoverToolsParams(BaseModel):
    """Parameters for discovering tools."""
    categories: Optional[List[str]] = Field(
        None,
        description="Filter by category: 'calendar', 'gmail', 'tasks'"
    )
    actions: Optional[List[str]] = Field(
        None,
        description="Filter by action type: 'search', 'create', 'update', 'delete', 'list', 'read'"
    )
    query: Optional[str] = Field(
        None,
        description="Keyword to search in tool names and descriptions"
    )


class GetToolSchemaParams(BaseModel):
    """Parameters for getting a tool's schema."""
    tool_name: str = Field(
        ...,
        description="The exact tool name from discover_tools results"
    )


class InvokeToolParams(BaseModel):
    """Parameters for invoking a tool."""
    tool_name: str = Field(
        ...,
        description="The tool to execute"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters matching the tool's schema from get_tool_schema"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Meta-Tool Implementations
# ─────────────────────────────────────────────────────────────────────────────

class MetaTools:
    """
    Meta-tools for lazy tool loading.
    
    These three tools let the LLM discover and invoke tools on-demand,
    rather than loading all tool schemas into context upfront.
    """
    
    def __init__(self, tool_registry):
        """
        Initialize meta-tools with a tool registry.
        
        Args:
            tool_registry: AgentTools instance that can execute tools
        """
        self.tool_registry = tool_registry
        self._pending_confirmation = None
    
    def discover_tools(
        self,
        categories: Optional[List[str]] = None,
        actions: Optional[List[str]] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Find available tools by category and/or action type.
        
        This returns lightweight metadata (~15 tokens per tool) instead of
        full schemas (~400 tokens per tool).
        
        Args:
            categories: Filter by category (calendar, gmail, tasks)
            actions: Filter by action (search, create, update, delete, list, read)
            query: Keyword search in tool names and summaries
            
        Returns:
            List of matching tools with name, summary, and metadata
        """
        return _discover_tools(categories=categories, actions=actions, query=query)
    
    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get the complete parameter schema for a specific tool.
        
        Only loads the full schema when actually needed, saving tokens.
        
        Args:
            tool_name: The exact tool name from discover_tools
            
        Returns:
            Full tool definition including all parameters
        """
        registry = self.tool_registry.get_tool_registry()
        tool_info = registry.get(tool_name)
        
        if not tool_info:
            return {
                "error": f"Unknown tool: {tool_name}",
                "hint": "Use discover_tools to find available tools",
            }
        
        # Get schema from Pydantic model
        model = tool_info["model"]
        schema = model.model_json_schema()
        
        # Get metadata from index
        meta = TOOL_INDEX.get(tool_name)
        is_write = meta.is_write if meta else False
        
        return {
            "name": tool_name,
            "description": tool_info["description"],
            "parameters": schema.get("properties", {}),
            "required": schema.get("required", []),
            "is_write": is_write,
            "hint": "Destructive operations require user confirmation" if is_write else "Ready to invoke",
        }
    
    def invoke_tool(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a tool with the given parameters.
        
        For write operations (create, update, delete), this may return a
        pending_confirmation status instead of executing immediately.
        
        Args:
            tool_name: The tool to execute
            parameters: Parameters matching the tool's schema
            
        Returns:
            The tool's result, or a confirmation request for write ops
        """
        if parameters is None:
            parameters = {}
        
        # Check if this is a destructive operation requiring confirmation
        meta = TOOL_INDEX.get(tool_name)
        if meta and meta.is_write and "delete" in meta.actions:
            # Store pending action for confirmation flow
            self._pending_confirmation = {
                "tool_name": tool_name,
                "parameters": parameters,
                "summary": f"Delete operation: {tool_name}",
            }
            return {
                "status": "pending_confirmation",
                "tool_name": tool_name,
                "parameters": parameters,
                "message": "This action requires user confirmation before execution",
            }
        
        # Execute the tool
        return self.tool_registry.execute_tool(tool_name, parameters)
    
    def get_pending_confirmation(self) -> Optional[Dict[str, Any]]:
        """Get any pending confirmation request."""
        return self._pending_confirmation
    
    def clear_pending_confirmation(self):
        """Clear pending confirmation after user responds."""
        self._pending_confirmation = None
    
    def execute_pending(self) -> Dict[str, Any]:
        """Execute the pending confirmed action."""
        if not self._pending_confirmation:
            return {"error": "No pending action to execute"}
        
        result = self.tool_registry.execute_tool(
            self._pending_confirmation["tool_name"],
            self._pending_confirmation["parameters"],
        )
        self.clear_pending_confirmation()
        return result
    
    def get_langchain_tools(self) -> List[StructuredTool]:
        """
        Get the three meta-tools as LangChain StructuredTools.
        
        Returns:
            List of 3 StructuredTool instances (~550 tokens total)
        """
        return [
            StructuredTool.from_function(
                func=self.discover_tools,
                name="discover_tools",
                description=(
                    "Find available tools by category and/or action type. "
                    "Categories: calendar, gmail, tasks. "
                    "Actions: search, create, update, delete, list, read. "
                    "Use this first to find what tools are available."
                ),
                args_schema=DiscoverToolsParams,
            ),
            StructuredTool.from_function(
                func=self.get_tool_schema,
                name="get_tool_schema",
                description=(
                    "Get the complete parameter schema for a specific tool. "
                    "Use this to understand required/optional parameters before invoking. "
                    "For simple tools like 'list_tasks', you may skip this and invoke directly."
                ),
                args_schema=GetToolSchemaParams,
            ),
            StructuredTool.from_function(
                func=self.invoke_tool,
                name="invoke_tool",
                description=(
                    "Execute a tool with the given parameters. "
                    "Destructive operations (delete) will require user confirmation. "
                    "For most tools, provide the tool_name and parameters dict."
                ),
                args_schema=InvokeToolParams,
            ),
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────────────────────

def create_meta_tools(tool_registry) -> MetaTools:
    """
    Create meta-tools instance for an agent.
    
    Args:
        tool_registry: AgentTools instance
        
    Returns:
        MetaTools instance with discover, schema, and invoke tools
    """
    return MetaTools(tool_registry)


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt Addition for Meta-Tools
# ─────────────────────────────────────────────────────────────────────────────

META_TOOLS_SYSTEM_PROMPT = """
## How to use tools

You have 3 meta-tools to access all functionality:

1. **discover_tools**: Find available tools by category/action/keyword
   - Categories: calendar, gmail, tasks
   - Actions: search, create, update, delete, list, read
   - Example: discover_tools(categories=["calendar"], actions=["create"])

2. **get_tool_schema**: Get full parameters for a specific tool
   - Use when you need to know exact parameter names and types
   - Example: get_tool_schema(tool_name="add_calendar_event")

3. **invoke_tool**: Execute a tool with parameters
   - Example: invoke_tool(tool_name="list_tasks", parameters={})

**Workflow:**
1. User asks something → use discover_tools to find relevant tools
2. For complex tools, use get_tool_schema to understand parameters
3. Use invoke_tool to execute with the right parameters

**Shortcuts (skip get_tool_schema for these simple tools):**
- list_tasks: invoke_tool(tool_name="list_tasks", parameters={})
- list_calendar_events: invoke_tool(tool_name="list_calendar_events", parameters={})
- list_unread_emails: invoke_tool(tool_name="list_unread_emails", parameters={})
- get_task_lists: invoke_tool(tool_name="get_task_lists", parameters={})

**Important:**
- Delete operations require user confirmation
- For current date/time, the date is provided in the system prompt
- When searching, discover tools first to find the right search tool
"""
