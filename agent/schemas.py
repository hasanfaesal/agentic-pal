from pydantic import BaseModel, Field
from typing import Optional, Callable, Any

# =============================================================================
# Pydantic Models for Tool Parameters
# =============================================================================

# Calendar Tool Models
class AddCalendarEventParams(BaseModel):
    """Parameters for adding a calendar event."""
    title: str = Field(..., description="The title/summary of the event")
    start_time: str = Field(..., description="Start date/time (e.g., 'tomorrow at 2pm', '2026-01-21T14:00:00', 'next Tuesday')")
    end_time: Optional[str] = Field(None, description="End date/time. If not provided, defaults to 1 hour after start")
    duration: Optional[str] = Field(None, description="Duration of the event (e.g., '1 hour', '30 minutes'). Used if end_time not provided")
    description: Optional[str] = Field("", description="Event description or notes")
    attendees: Optional[list[str]] = Field(None, description="List of attendee email addresses")
    timezone: Optional[str] = Field("UTC", description="Timezone for the event (e.g., 'America/New_York', 'UTC')")


class DeleteCalendarEventParams(BaseModel):
    """Parameters for deleting a calendar event."""
    event_id: str = Field(..., description="The unique ID of the event to delete")


class SearchCalendarEventsParams(BaseModel):
    """Parameters for searching calendar events."""
    query: str = Field(..., description="Search term to find in event titles")
    max_results: Optional[int] = Field(5, description="Maximum number of events to return", ge=1, le=50)


class ListCalendarEventsParams(BaseModel):
    """Parameters for listing calendar events."""
    max_results: Optional[int] = Field(20, description="Maximum number of events to return", ge=1, le=100)
    time_min: Optional[str] = Field(None, description="Start of time range (e.g., 'today', '2026-01-21')")
    time_max: Optional[str] = Field(None, description="End of time range (e.g., 'next week', '2026-01-28')")


class UpdateCalendarEventParams(BaseModel):
    """Parameters for updating a calendar event."""
    event_id: str = Field(..., description="The unique ID of the event to update")
    title: Optional[str] = Field(None, description="New event title")
    start_time: Optional[str] = Field(None, description="New start date/time")
    end_time: Optional[str] = Field(None, description="New end date/time")
    description: Optional[str] = Field(None, description="New event description")


# Task Tool Models
class CreateTaskParams(BaseModel):
    """Parameters for creating a task."""
    title: str = Field(..., description="The title of the task")
    due: Optional[str] = Field(None, description="Due date (e.g., 'tomorrow', '2026-01-25', 'next Friday')")
    notes: Optional[str] = Field("", description="Additional notes for the task")
    tasklist: Optional[str] = Field(None, description="Task list ID. If not provided, uses default list")


class ListTasksParams(BaseModel):
    """Parameters for listing tasks."""
    tasklist: Optional[str] = Field(None, description="Task list ID. If not provided, uses default list")
    show_completed: Optional[bool] = Field(False, description="Include completed tasks in results")
    max_results: Optional[int] = Field(20, description="Maximum number of tasks to return", ge=1, le=100)


class MarkTaskCompleteParams(BaseModel):
    """Parameters for marking a task as complete."""
    task_id: str = Field(..., description="The unique ID of the task to mark complete")
    tasklist: Optional[str] = Field(None, description="Task list ID. If not provided, uses default list")


class MarkTaskIncompleteParams(BaseModel):
    """Parameters for marking a task as incomplete."""
    task_id: str = Field(..., description="The unique ID of the task to mark incomplete")
    tasklist: Optional[str] = Field(None, description="Task list ID. If not provided, uses default list")


class DeleteTaskParams(BaseModel):
    """Parameters for deleting a task."""
    task_id: str = Field(..., description="The unique ID of the task to delete")
    tasklist: Optional[str] = Field(None, description="Task list ID. If not provided, uses default list")


class UpdateTaskParams(BaseModel):
    """Parameters for updating a task."""
    task_id: str = Field(..., description="The unique ID of the task to update")
    tasklist: Optional[str] = Field(None, description="Task list ID. If not provided, uses default list")
    title: Optional[str] = Field(None, description="New task title")
    due: Optional[str] = Field(None, description="New due date")
    notes: Optional[str] = Field(None, description="New notes")


class GetTaskListsParams(BaseModel):
    """Parameters for getting task lists (no parameters needed)."""
    pass


# Gmail Tool Models
class ReadEmailsParams(BaseModel):
    """Parameters for reading/listing emails."""
    query: Optional[str] = Field("", description="Gmail search query (e.g., 'from:sender@example.com', 'is:unread', 'subject:meeting')")
    max_results: Optional[int] = Field(10, description="Maximum number of emails to return", ge=1, le=50)


class GetEmailDetailsParams(BaseModel):
    """Parameters for getting full email details."""
    message_id: str = Field(..., description="The unique ID of the email message")


class SummarizeWeeklyEmailsParams(BaseModel):
    """Parameters for getting weekly email summary."""
    days: Optional[int] = Field(7, description="Number of days to look back", ge=1, le=30)
    max_results: Optional[int] = Field(20, description="Maximum number of emails to include in summary", ge=1, le=100)


class SearchEmailsParams(BaseModel):
    """Parameters for searching emails."""
    query: str = Field(..., description="Gmail search query (e.g., 'subject:project', 'has:attachment', 'from:boss@company.com')")
    max_results: Optional[int] = Field(10, description="Maximum number of emails to return", ge=1, le=50)


class ListUnreadEmailsParams(BaseModel):
    """Parameters for listing unread emails."""
    max_results: Optional[int] = Field(10, description="Maximum number of unread emails to return", ge=1, le=50)
