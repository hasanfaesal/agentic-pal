"""
Agent tools registry.

Provides the AgentTools class that wraps service methods for agent use.
Uses tool_definitions.py
"""

from typing import Optional, Callable, Any, List

from langchain_core.tools import StructuredTool

from .tool_definitions import (
    TOOL_DEFINITIONS,
    BY_CATEGORY,
    get_tools_for_categories,
)
from ..date_utils import parse_datetime, calculate_end_time


class AgentTools:
    """
    Collection of tool wrapper functions for the agent.
    Wraps service methods and handles parameter parsing/validation.
    """

    def __init__(
        self,
        calendar_service,
        gmail_service,
        tasks_service,
        default_timezone: str = "UTC",
    ):
        """Initialize tools with service instances."""
        self.calendar = calendar_service
        self.gmail = gmail_service
        self.tasks = tasks_service
        self.default_timezone = default_timezone

        # Build tool registry from definitions
        self._tool_registry = self._build_tool_registry()
    
    def _build_tool_registry(self) -> dict[str, dict]:
        """
        Build registry mapping tool names to functions and schemas.
        
        Uses TOOL_DEFINITIONS as the source of truth, binding to instance methods.
        """
        registry = {}
        
        for name, defn in TOOL_DEFINITIONS.items():
            # Get the method from this instance
            method = getattr(self, defn.method_name, None)
            if method is None:
                raise AttributeError(
                    f"Tool '{name}' references method '{defn.method_name}' "
                    f"which does not exist on AgentTools"
                )
            
            registry[name] = {
                "function": method,
                "model": defn.schema,
                "description": defn.description,
            }
        
        return registry
    
    # ─────────────────────────────────────────────────────────────────────
    # Registry Access Methods
    # ─────────────────────────────────────────────────────────────────────
    
    def get_tool_registry(self) -> dict[str, dict]:
        """Get the tool registry."""
        return self._tool_registry
    
    def get_tool_names(self) -> list[str]:
        """Get list of all available tool names."""
        return list(self._tool_registry.keys())
    
    def get_langchain_tools(self) -> List[StructuredTool]:
        """
        Convert the tool registry to LangChain StructuredTool format.
        
        Returns:
            List of StructuredTool instances for LLM binding
        """
        langchain_tools = []
        
        for name, tool_info in self._tool_registry.items():
            tool = StructuredTool.from_function(
                func=tool_info["function"],
                name=name,
                description=tool_info["description"],
                args_schema=tool_info["model"],
            )
            langchain_tools.append(tool)
        
        return langchain_tools
    
    def get_langchain_tools_for_categories(self, categories: list[str]) -> List[StructuredTool]:
        """
        Get LangChain tools filtered by categories.
        
        Args:
            categories: List of category names (e.g., ["calendar", "tasks"])
            
        Returns:
            List of StructuredTool instances for the specified categories
        """
        tool_names = get_tools_for_categories(categories)
        
        return [
            tool for tool in self.get_langchain_tools()
            if tool.name in tool_names
        ]
    
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
    
    # ─────────────────────────────────────────────────────────────────────
    # Calendar Tools
    # ─────────────────────────────────────────────────────────────────────
    
    def add_calendar_event(
        self,
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        duration: Optional[str] = None,
        description: str = "",
        attendees: Optional[list[str]] = None,
        timezone: str = "UTC",
    ) -> dict:
        """Add a new event to the calendar with parsed times."""
        try:
            parsed_start, is_all_day = parse_datetime(start_time, timezone)

            if is_all_day:
                return self.calendar.add_event(
                    title=title,
                    start_time=parsed_start + "T00:00:00",
                    end_time=parsed_start + "T23:59:59",
                    description=description,
                    attendees=attendees,
                    timezone=timezone,
                )

            if end_time:
                parsed_end, _ = parse_datetime(end_time, timezone)
            elif duration:
                parsed_end = calculate_end_time(parsed_start, duration)
            else:
                parsed_end = calculate_end_time(parsed_start, "1 hour")

            return self.calendar.add_event(
                title=title,
                start_time=parsed_start,
                end_time=parsed_end,
                description=description,
                attendees=attendees,
                timezone=timezone,
            )

        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid date/time: {e}",
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add event: {e}",
                "error": str(e),
            }

    def delete_calendar_event(self, event_id: str) -> dict:
        """Delete a calendar event by ID."""
        return self.calendar.delete_event(event_id)

    def search_calendar_events(self, query: str, max_results: int = 5) -> dict:
        """Search for calendar events by keyword."""
        return self.calendar.search_events(query=query, max_results=max_results)

    def list_calendar_events(
        self,
        max_results: int = 20,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
    ) -> dict:
        """List upcoming calendar events."""
        try:
            parsed_min = None
            parsed_max = None

            if time_min:
                parsed_min, _ = parse_datetime(time_min, self.default_timezone)
                if not parsed_min.endswith("Z"):
                    parsed_min += "Z"

            if time_max:
                parsed_max, _ = parse_datetime(time_max, self.default_timezone)
                if not parsed_max.endswith("Z"):
                    parsed_max += "Z"

            return self.calendar.list_events(
                max_results=max_results,
                time_min=parsed_min,
                time_max=parsed_max,
            )

        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid date/time: {e}",
                "error": str(e),
            }

    def update_calendar_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """Update an existing calendar event."""
        try:
            parsed_start = None
            parsed_end = None

            if start_time:
                parsed_start, _ = parse_datetime(start_time, self.default_timezone)

            if end_time:
                parsed_end, _ = parse_datetime(end_time, self.default_timezone)

            return self.calendar.update_event(
                event_id=event_id,
                title=title,
                start_time=parsed_start,
                end_time=parsed_end,
                description=description,
            )

        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid date/time: {e}",
                "error": str(e),
            }

    # ─────────────────────────────────────────────────────────────────────
    # Task Tools
    # ─────────────────────────────────────────────────────────────────────

    def create_task(
        self,
        title: str,
        due: Optional[str] = None,
        notes: str = "",
        tasklist: Optional[str] = None,
    ) -> dict:
        """Create a new task."""
        try:
            parsed_due = None
            if due:
                parsed_due, _ = parse_datetime(due, self.default_timezone)
                if not parsed_due.endswith("Z"):
                    parsed_due = parsed_due.split("T")[0] + "T00:00:00.000Z"

            return self.tasks.create_task(
                title=title,
                tasklist=tasklist,
                due=parsed_due,
                notes=notes,
            )

        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid due date: {e}",
                "error": str(e),
            }

    def list_tasks(
        self,
        tasklist: Optional[str] = None,
        show_completed: bool = False,
        max_results: int = 20,
    ) -> dict:
        """List tasks from a task list."""
        return self.tasks.list_tasks(
            tasklist=tasklist,
            show_completed=show_completed,
            max_results=max_results,
        )

    def mark_task_complete(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
    ) -> dict:
        """Mark a task as completed."""
        return self.tasks.mark_task_complete(task_id=task_id, tasklist=tasklist)

    def mark_task_incomplete(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
    ) -> dict:
        """Mark a task as incomplete."""
        return self.tasks.mark_task_incomplete(task_id=task_id, tasklist=tasklist)

    def delete_task(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
    ) -> dict:
        """Delete a task."""
        return self.tasks.delete_task(task_id=task_id, tasklist=tasklist)

    def update_task(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
        title: Optional[str] = None,
        due: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Update a task."""
        try:
            parsed_due = None
            if due:
                parsed_due, _ = parse_datetime(due, self.default_timezone)
                if not parsed_due.endswith("Z"):
                    parsed_due = parsed_due.split("T")[0] + "T00:00:00.000Z"

            return self.tasks.update_task(
                task_id=task_id,
                tasklist=tasklist,
                title=title,
                due=parsed_due,
                notes=notes,
            )

        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid due date: {e}",
                "error": str(e),
            }

    def get_task_lists(self) -> dict:
        """Get all task lists."""
        return self.tasks.get_task_lists()

    # ─────────────────────────────────────────────────────────────────────
    # Gmail Tools
    # ─────────────────────────────────────────────────────────────────────

    def read_emails(
        self,
        query: str = "",
        max_results: int = 10,
    ) -> dict:
        """Read/list emails with optional query filter."""
        return self.gmail.list_messages(query=query, max_results=max_results)

    def get_email_details(self, message_id: str) -> dict:
        """Get full details of a specific email."""
        return self.gmail.get_message_full(message_id=message_id)

    def summarize_weekly_emails(
        self,
        days: int = 7,
        max_results: int = 20,
    ) -> dict:
        """Get a summary of emails from the past N days."""
        return self.gmail.weekly_summary(days=days, max_results=max_results)

    def search_emails(
        self,
        query: str,
        max_results: int = 10,
    ) -> dict:
        """Search emails using Gmail search syntax."""
        return self.gmail.search_messages(query=query, max_results=max_results)

    def list_unread_emails(self, max_results: int = 10) -> dict:
        """List unread emails."""
        return self.gmail.list_unread_messages(max_results=max_results)
