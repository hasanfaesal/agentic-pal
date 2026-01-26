"""
Tool index for lazy loading.
Contains minimal metadata for tool discovery without loading full schemas.

This module now derives its data from tool_definitions.py.
This approach reduces token usage by 96-97% compared to loading all tool
definitions upfront. See lazy-tool-loading.md for details.
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
import json

from .tool_definitions import (
    TOOL_DEFINITIONS,
    BY_CATEGORY,
    BY_ACTION,
)


@dataclass
class ToolMetadata:
    """Minimal metadata for tool discovery (lightweight view of ToolDefinition)."""
    name: str
    summary: str  # Short description (10-20 tokens)
    category: str  # "calendar", "gmail", "tasks"
    actions: List[str]  # ["search", "create", "delete", etc.]
    is_write: bool  # Requires confirmation


def _build_tool_index() -> Dict[str, ToolMetadata]:
    """Build TOOL_INDEX from TOOL_DEFINITIONS."""
    return {
        name: ToolMetadata(
            name=defn.name,
            summary=defn.summary,
            category=defn.category,
            actions=defn.actions,
            is_write=defn.is_write,
        )
        for name, defn in TOOL_DEFINITIONS.items()
    }


# Build the index at import time
TOOL_INDEX: Dict[str, ToolMetadata] = _build_tool_index()


# ─────────────────────────────────────────────────────────────────────────────
# Tool Index Functions
# ─────────────────────────────────────────────────────────────────────────────

def discover_tools(
    categories: Optional[List[str]] = None,
    actions: Optional[List[str]] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find available tools by category, action, or keyword search.
    
    Args:
        categories: Filter by category (calendar, gmail, tasks)
        actions: Filter by action type (search, create, update, delete, list, read)
        query: Keyword search in tool names and summaries
        
    Returns:
        Dict with matching tools and their metadata
    """
    # Start with all tools
    matching_names: Set[str] = set(TOOL_INDEX.keys())
    
    # Filter by category
    if categories:
        category_tools: Set[str] = set()
        for cat in categories:
            if cat in BY_CATEGORY:
                category_tools.update(BY_CATEGORY[cat])
        matching_names &= category_tools
    
    # Filter by action
    if actions:
        action_tools: Set[str] = set()
        for action in actions:
            if action in BY_ACTION:
                action_tools.update(BY_ACTION[action])
        matching_names &= action_tools
    
    # Filter by keyword search
    if query:
        query_lower = query.lower()
        keyword_tools: Set[str] = set()
        for name in matching_names:
            meta = TOOL_INDEX[name]
            if query_lower in name.lower() or query_lower in meta.summary.lower():
                keyword_tools.add(name)
        matching_names = keyword_tools
    
    # Build result
    tools = []
    for name in sorted(matching_names):
        meta = TOOL_INDEX[name]
        tools.append({
            "name": meta.name,
            "summary": meta.summary,
            "category": meta.category,
            "is_write": meta.is_write,
        })
    
    return {
        "tools": tools,
        "count": len(tools),
        "hint": "Use get_tool_schema to see full parameters, then invoke_tool to execute",
    }


def get_tool_metadata(tool_name: str) -> Optional[ToolMetadata]:
    """Get metadata for a specific tool."""
    return TOOL_INDEX.get(tool_name)


def get_tools_by_category(category: str) -> List[str]:
    """Get tool names for a specific category."""
    return BY_CATEGORY.get(category, [])


def get_tools_by_action(action: str) -> List[str]:
    """Get tool names for a specific action type."""
    return BY_ACTION.get(action, [])


def export_index_to_json() -> str:
    """Export the tool index to JSON format (for build-time generation)."""
    return json.dumps({
        "tools": {name: asdict(meta) for name, meta in TOOL_INDEX.items()},
        "by_category": BY_CATEGORY,
        "by_action": BY_ACTION,
    }, indent=2)
