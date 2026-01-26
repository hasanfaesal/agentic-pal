"""
Agent tools module.

Provides tool registry and lazy loading capabilities.
"""

from .registry import AgentTools
from .meta_tools import MetaTools, create_meta_tools, META_TOOLS_SYSTEM_PROMPT
from .tool_definitions import (
    TOOL_DEFINITIONS,
    ToolDefinition,
    BY_CATEGORY,
    BY_ACTION,
    TOOL_TO_CATEGORY,
    get_tool_definition,
    get_tools_for_categories,
    get_category_for_tool,
    get_all_categories,
    get_all_actions,
    get_all_tool_names,
)
from .tool_index import (
    TOOL_INDEX,
    ToolMetadata,
    discover_tools,
    get_tool_metadata,
    get_tools_by_category,
    get_tools_by_action,
)

__all__ = [
    # Registry
    "AgentTools",
    
    # Meta-tools for lazy loading
    "MetaTools",
    "create_meta_tools",
    "META_TOOLS_SYSTEM_PROMPT",
    
    # Tool definitions
    "TOOL_DEFINITIONS",
    "ToolDefinition",
    "BY_CATEGORY",
    "BY_ACTION",
    "TOOL_TO_CATEGORY",
    "get_tool_definition",
    "get_tools_for_categories",
    "get_category_for_tool",
    "get_all_categories",
    "get_all_actions",
    "get_all_tool_names",
    
    # Tool index (lightweight discovery)
    "TOOL_INDEX",
    "ToolMetadata",
    "discover_tools",
    "get_tool_metadata",
    "get_tools_by_category",
    "get_tools_by_action",
]
