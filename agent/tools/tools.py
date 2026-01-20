from typing import Optional, Callable, Any

from .. import schemas
from .tools_calendar import CalendarToolsMixin
from .tools_tasks import TasksToolsMixin
from .tools_gmail import GmailToolsMixin


# =============================================================================
# Tool Wrapper Functions
# =============================================================================

class AgentTools(CalendarToolsMixin, TasksToolsMixin, GmailToolsMixin):
    """
    Collection of tool wrapper functions for the agent.
    Wraps service methods and handles parameter parsing/validation.
    """

    def __init__(self, calendar_service, gmail_service, tasks_service, default_timezone: str = "UTC"):
        """Initialize tools with service instances."""
        self.calendar = calendar_service
        self.gmail = gmail_service
        self.tasks = tasks_service
        self.default_timezone = default_timezone

        # Build tool registry
        self._tool_registry = self._build_tool_registry()
    
    def _build_tool_registry(self) -> dict[str, dict]:
        """Build registry mapping tool names to functions and schemas."""
        return {
            # Calendar tools
            "add_calendar_event": {
                "function": self.add_calendar_event,
                "model": schemas.AddCalendarEventParams,
                "description": "Add a new event to the user's Google Calendar. Use this when the user wants to schedule a meeting, appointment, or any calendar event.",
            },
            "delete_calendar_event": {
                "function": self.delete_calendar_event,
                "model": schemas.DeleteCalendarEventParams,
                "description": "Delete an event from the user's Google Calendar by its event ID. Always confirm with the user before deleting.",
            },
            "search_calendar_events": {
                "function": self.search_calendar_events,
                "model": schemas.SearchCalendarEventsParams,
                "description": "Search for calendar events by title/keyword. Use this to find specific events before updating or deleting them.",
            },
            "list_calendar_events": {
                "function": self.list_calendar_events,
                "model": schemas.ListCalendarEventsParams,
                "description": "List upcoming calendar events within a time range. Use this to show the user their schedule.",
            },
            "update_calendar_event": {
                "function": self.update_calendar_event,
                "model": schemas.UpdateCalendarEventParams,
                "description": "Update an existing calendar event. Can modify title, times, or description.",
            },
            # Task tools
            "create_task": {
                "function": self.create_task,
                "model": schemas.CreateTaskParams,
                "description": "Create a new task in Google Tasks. Use this when the user wants to add a todo item or reminder.",
            },
            "list_tasks": {
                "function": self.list_tasks,
                "model": schemas.ListTasksParams,
                "description": "List tasks from Google Tasks. Shows incomplete tasks by default.",
            },
            "mark_task_complete": {
                "function": self.mark_task_complete,
                "model": schemas.MarkTaskCompleteParams,
                "description": "Mark a task as completed. Use this when the user says they finished a task.",
            },
            "mark_task_incomplete": {
                "function": self.mark_task_incomplete,
                "model": schemas.MarkTaskIncompleteParams,
                "description": "Mark a task as incomplete/not done. Use this to reopen a completed task.",
            },
            "delete_task": {
                "function": self.delete_task,
                "model": schemas.DeleteTaskParams,
                "description": "Delete a task from Google Tasks. Always confirm with the user before deleting.",
            },
            "update_task": {
                "function": self.update_task,
                "model": schemas.UpdateTaskParams,
                "description": "Update an existing task. Can modify title, due date, or notes.",
            },
            "get_task_lists": {
                "function": self.get_task_lists,
                "model": schemas.GetTaskListsParams,
                "description": "Get all available task lists. Use this to find task list IDs.",
            },
            # Gmail tools
            "read_emails": {
                "function": self.read_emails,
                "model": schemas.ReadEmailsParams,
                "description": "Read/list recent emails from Gmail. Can filter by sender, label, or search query.",
            },
            "get_email_details": {
                "function": self.get_email_details,
                "model": schemas.GetEmailDetailsParams,
                "description": "Get full details of a specific email including the body content.",
            },
            "summarize_weekly_emails": {
                "function": self.summarize_weekly_emails,
                "model": schemas.SummarizeWeeklyEmailsParams,
                "description": "Get a summary of emails from the past week (or specified days). Shows top senders and sample subjects.",
            },
            "search_emails": {
                "function": self.search_emails,
                "model": schemas.SearchEmailsParams,
                "description": "Search emails using Gmail search syntax (e.g., 'subject:meeting', 'from:boss@company.com', 'has:attachment').",
            },
            "list_unread_emails": {
                "function": self.list_unread_emails,
                "model": schemas.ListUnreadEmailsParams,
                "description": "List unread emails from the inbox.",
            },
        }
    
    def get_tool_registry(self) -> dict[str, dict]:
        """Get the tool registry."""
        return self._tool_registry
    
    def get_tool_names(self) -> list[str]:
        """Get list of all available tool names."""
        return list(self._tool_registry.keys())
    
    def get_tool_function(self, name: str) -> Optional[Callable]:
        """Get the function for a tool by name."""
        tool = self._tool_registry.get(name)
        return tool["function"] if tool else None
    
    def execute_tool(self, name: str, arguments: dict) -> dict:
        """
        Execute a tool by name with given arguments.
        
        Args:
            name: Tool name
            arguments: Dict of arguments for the tool
            
        Returns:
            Tool execution result dict
        """
        tool = self._tool_registry.get(name)
        if not tool:
            return {
                "success": False,
                "message": f"Unknown tool: {name}",
                "error": f"Tool '{name}' not found in registry",
            }
        
        try:
            # Validate arguments with Pydantic model
            model = tool["model"]
            validated_params = model(**arguments)
            
            # Execute the function
            func = tool["function"]
            result = func(**validated_params.model_dump())
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error executing {name}: {str(e)}",
                "error": str(e),
            }