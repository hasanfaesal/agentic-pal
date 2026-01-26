from typing import Dict, List, Set, Optional, Any, Type
from dataclasses import dataclass, field
from pydantic import BaseModel

from .. import schemas


@dataclass
class ToolDefinition:
    name: str
    summary: str  # Short description for discovery (~15 tokens)
    description: str  # Full description for LLM tool binding
    category: str  # "calendar", "gmail", "tasks"
    actions: List[str]  # ["search", "create", "delete", etc.]
    is_write: bool  # Requires confirmation for destructive ops
    schema: Type[BaseModel]  # Pydantic model for parameters
    method_name: str = field(default="")  # Method name on AgentTools (defaults to tool name)
    
    def __post_init__(self):
        if not self.method_name:
            self.method_name = self.name


# ─────────────────────────────────────────────────────────────────────────────
# Tool Definitions
# ─────────────────────────────────────────────────────────────────────────────

TOOL_DEFINITIONS: Dict[str, ToolDefinition] = {
    # ─────────────────────────────────────────────────────────────────────
    # Calendar Tools
    # ─────────────────────────────────────────────────────────────────────
    "add_calendar_event": ToolDefinition(
        name="add_calendar_event",
        summary="Create a new calendar event with title, time, and optional attendees",
        description="Add a new event to the user's Google Calendar. Use this when the user wants to schedule a meeting, appointment, or any calendar event.",
        category="calendar",
        actions=["create", "write"],
        is_write=True,
        schema=schemas.AddCalendarEventParams,
    ),
    "delete_calendar_event": ToolDefinition(
        name="delete_calendar_event",
        summary="Delete a calendar event by its ID",
        description="Delete an event from the user's Google Calendar by its event ID. Always confirm with the user before deleting.",
        category="calendar",
        actions=["delete", "write"],
        is_write=True,
        schema=schemas.DeleteCalendarEventParams,
    ),
    "search_calendar_events": ToolDefinition(
        name="search_calendar_events",
        summary="Search for events by title keyword",
        description="Search for calendar events by title/keyword. Use this to find specific events before updating or deleting them.",
        category="calendar",
        actions=["search", "read"],
        is_write=False,
        schema=schemas.SearchCalendarEventsParams,
    ),
    "list_calendar_events": ToolDefinition(
        name="list_calendar_events",
        summary="List upcoming calendar events in a time range",
        description="List upcoming calendar events within a time range. Use this to show the user their schedule.",
        category="calendar",
        actions=["list", "read"],
        is_write=False,
        schema=schemas.ListCalendarEventsParams,
    ),
    "update_calendar_event": ToolDefinition(
        name="update_calendar_event",
        summary="Update an existing calendar event's details",
        description="Update an existing calendar event. Can modify title, times, or description.",
        category="calendar",
        actions=["update", "write"],
        is_write=True,
        schema=schemas.UpdateCalendarEventParams,
    ),
    
    # ─────────────────────────────────────────────────────────────────────
    # Task Tools
    # ─────────────────────────────────────────────────────────────────────
    "create_task": ToolDefinition(
        name="create_task",
        summary="Create a new task/todo item with optional due date",
        description="Create a new task in Google Tasks. Use this when the user wants to add a todo item or reminder.",
        category="tasks",
        actions=["create", "write"],
        is_write=True,
        schema=schemas.CreateTaskParams,
    ),
    "list_tasks": ToolDefinition(
        name="list_tasks",
        summary="List tasks from a task list",
        description="List tasks from Google Tasks. Shows incomplete tasks by default.",
        category="tasks",
        actions=["list", "read"],
        is_write=False,
        schema=schemas.ListTasksParams,
    ),
    "mark_task_complete": ToolDefinition(
        name="mark_task_complete",
        summary="Mark a task as completed/done",
        description="Mark a task as completed. Use this when the user says they finished a task.",
        category="tasks",
        actions=["update", "write"],
        is_write=True,
        schema=schemas.MarkTaskCompleteParams,
    ),
    "mark_task_incomplete": ToolDefinition(
        name="mark_task_incomplete",
        summary="Mark a task as incomplete/not done",
        description="Mark a task as incomplete/not done. Use this to reopen a completed task.",
        category="tasks",
        actions=["update", "write"],
        is_write=True,
        schema=schemas.MarkTaskIncompleteParams,
    ),
    "delete_task": ToolDefinition(
        name="delete_task",
        summary="Delete a task by its ID",
        description="Delete a task from Google Tasks. Always confirm with the user before deleting.",
        category="tasks",
        actions=["delete", "write"],
        is_write=True,
        schema=schemas.DeleteTaskParams,
    ),
    "update_task": ToolDefinition(
        name="update_task",
        summary="Update a task's title, due date, or notes",
        description="Update an existing task. Can modify title, due date, or notes.",
        category="tasks",
        actions=["update", "write"],
        is_write=True,
        schema=schemas.UpdateTaskParams,
    ),
    "get_task_lists": ToolDefinition(
        name="get_task_lists",
        summary="Get all available task lists",
        description="Get all available task lists. Use this to find task list IDs.",
        category="tasks",
        actions=["list", "read"],
        is_write=False,
        schema=schemas.GetTaskListsParams,
    ),
    
    # ─────────────────────────────────────────────────────────────────────
    # Gmail Tools
    # ─────────────────────────────────────────────────────────────────────
    "read_emails": ToolDefinition(
        name="read_emails",
        summary="Read/list recent emails with optional filters",
        description="Read/list recent emails from Gmail. Can filter by sender, label, or search query.",
        category="gmail",
        actions=["list", "read"],
        is_write=False,
        schema=schemas.ReadEmailsParams,
    ),
    "get_email_details": ToolDefinition(
        name="get_email_details",
        summary="Get full details of a specific email including body",
        description="Get full details of a specific email including the body content.",
        category="gmail",
        actions=["read"],
        is_write=False,
        schema=schemas.GetEmailDetailsParams,
    ),
    "summarize_weekly_emails": ToolDefinition(
        name="summarize_weekly_emails",
        summary="Get a summary of emails from the past week",
        description="Get a summary of emails from the past week (or specified days). Shows top senders and sample subjects.",
        category="gmail",
        actions=["read", "summarize"],
        is_write=False,
        schema=schemas.SummarizeWeeklyEmailsParams,
    ),
    "search_emails": ToolDefinition(
        name="search_emails",
        summary="Search emails using Gmail search syntax",
        description="Search emails using Gmail search syntax (e.g., 'subject:meeting', 'from:boss@company.com', 'has:attachment').",
        category="gmail",
        actions=["search", "read"],
        is_write=False,
        schema=schemas.SearchEmailsParams,
    ),
    "list_unread_emails": ToolDefinition(
        name="list_unread_emails",
        summary="List unread emails from inbox",
        description="List unread emails from the inbox.",
        category="gmail",
        actions=["list", "read"],
        is_write=False,
        schema=schemas.ListUnreadEmailsParams,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Derived Indexes (built once at import time)
# ─────────────────────────────────────────────────────────────────────────────

# Category index: category -> [tool_names]
BY_CATEGORY: Dict[str, List[str]] = {}
for name, defn in TOOL_DEFINITIONS.items():
    BY_CATEGORY.setdefault(defn.category, []).append(name)

# Action index: action -> [tool_names]
BY_ACTION: Dict[str, List[str]] = {}
for name, defn in TOOL_DEFINITIONS.items():
    for action in defn.actions:
        BY_ACTION.setdefault(action, []).append(name)

# Reverse mapping: tool_name -> category (for legacy compatibility)
TOOL_TO_CATEGORY: Dict[str, str] = {
    name: defn.category for name, defn in TOOL_DEFINITIONS.items()
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def get_tool_definition(name: str) -> Optional[ToolDefinition]:
    """Get the full definition for a tool."""
    return TOOL_DEFINITIONS.get(name)


def get_tools_for_categories(categories: List[str]) -> Set[str]:
    """
    Get tool names for given categories.
    
    Args:
        categories: List of category names (e.g., ["calendar", "tasks"])
        
    Returns:
        Set of tool names belonging to those categories
    """
    tool_names = set()
    for category in categories:
        tool_names.update(BY_CATEGORY.get(category, []))
    return tool_names


def get_category_for_tool(tool_name: str) -> str:
    """Get the category for a tool, or 'unknown' if not found."""
    return TOOL_TO_CATEGORY.get(tool_name, "unknown")


def get_all_categories() -> List[str]:
    """Get all available tool categories."""
    return list(BY_CATEGORY.keys())


def get_all_actions() -> List[str]:
    """Get all available action types."""
    return list(BY_ACTION.keys())


def get_all_tool_names() -> List[str]:
    """Get all tool names."""
    return list(TOOL_DEFINITIONS.keys())
