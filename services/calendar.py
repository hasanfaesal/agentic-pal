"""Google Calendar service module for adding, deleting, and listing events.

Based on Google Workspace API quickstart example:
https://github.com/googleworkspace/python-samples/tree/main/calendar/quickstart
"""

from datetime import datetime, timedelta
from typing import Optional
from googleapiclient.errors import HttpError


class CalendarService:
    """Handles Calendar API interactions."""

    def __init__(self, service):
        """Initialize with authenticated Google Calendar service."""
        self.service = service
        self.primary_calendar_id = "primary"

    def add_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: Optional[list[str]] = None,
        timezone: str = "UTC",
    ) -> dict:
        """
        Add an event to the primary calendar.

        Args:
            title: Event title
            start_time: ISO format string or human-readable datetime (e.g., "2025-01-21T14:00:00")
            end_time: ISO format string or human-readable datetime
            description: Event description
            attendees: List of email addresses
            timezone: Timezone for the event (default: UTC)

        Returns:
            Dict with event ID and confirmation message
        """
        try:
            event = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_time,
                    "timeZone": timezone,
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": timezone,
                },
            }

            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]

            created_event = (
                self.service.events()
                .insert(calendarId=self.primary_calendar_id, body=event)
                .execute()
            )

            return {
                "success": True,
                "event_id": created_event["id"],
                "message": f"Event '{title}' created successfully.",
                "event": created_event,
            }

        except HttpError as error:
            return {
                "success": False,
                "message": f"Failed to create event: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error creating event: {e}",
                "error": str(e),
            }

    def delete_event(self, event_id: str) -> dict:
        """
        Delete an event from the primary calendar.

        Args:
            event_id: The ID of the event to delete

        Returns:
            Dict with confirmation message
        """
        try:
            self.service.events().delete(
                calendarId=self.primary_calendar_id, eventId=event_id
            ).execute()

            return {
                "success": True,
                "message": f"Event '{event_id}' deleted successfully.",
            }

        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Event '{event_id}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to delete event: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error deleting event: {e}",
                "error": str(e),
            }

    def list_events(
        self,
        max_results: int = 20,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
    ) -> dict:
        """
        List events from the primary calendar.

        Args:
            max_results: Maximum number of events to return
            time_min: ISO format start time (e.g., "2025-01-21T00:00:00Z")
            time_max: ISO format end time (e.g., "2025-01-21T23:59:59Z")

        Returns:
            Dict with list of events
        """
        try:
            # Default: today to 1 year ahead if no time range specified
            if not time_min:
                time_min = datetime.utcnow().isoformat() + "Z"
            if not time_max:
                time_max = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"

            events_result = (
                self.service.events()
                .list(
                    calendarId=self.primary_calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            if not events:
                return {
                    "success": True,
                    "message": "No events found.",
                    "events": [],
                }

            formatted_events = []
            for event in events:
                formatted_events.append({
                    "id": event["id"],
                    "title": event.get("summary", "No title"),
                    "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
                    "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date")),
                    "description": event.get("description", ""),
                })

            return {
                "success": True,
                "message": f"Found {len(formatted_events)} event(s).",
                "events": formatted_events,
            }

        except HttpError as error:
            return {
                "success": False,
                "message": f"Failed to list events: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error listing events: {e}",
                "error": str(e),
            }

    def search_events(self, query: str, max_results: int = 5) -> dict:
        """
        Search for events by title (simple text search).

        Args:
            query: Search term
            max_results: Maximum number of results

        Returns:
            Dict with matching events
        """
        try:
            time_min = datetime.utcnow().isoformat() + "Z"
            time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

            events_result = (
                self.service.events()
                .list(
                    calendarId=self.primary_calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    q=query,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            if not events:
                return {
                    "success": True,
                    "message": f"No events found matching '{query}'.",
                    "events": [],
                }

            formatted_events = []
            for event in events:
                formatted_events.append({
                    "id": event["id"],
                    "title": event.get("summary", "No title"),
                    "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
                    "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date")),
                })

            return {
                "success": True,
                "message": f"Found {len(formatted_events)} event(s) matching '{query}'.",
                "events": formatted_events,
            }

        except HttpError as error:
            return {
                "success": False,
                "message": f"Failed to search events: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error searching events: {e}",
                "error": str(e),
            }

    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Update an existing event.

        Args:
            event_id: The ID of the event to update
            title: New event title (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            description: New description (optional)

        Returns:
            Dict with confirmation message
        """
        try:
            # Fetch the event first
            event = (
                self.service.events()
                .get(calendarId=self.primary_calendar_id, eventId=event_id)
                .execute()
            )

            # Update only provided fields
            if title:
                event["summary"] = title
            if start_time:
                event["start"]["dateTime"] = start_time
            if end_time:
                event["end"]["dateTime"] = end_time
            if description:
                event["description"] = description

            updated_event = (
                self.service.events()
                .update(calendarId=self.primary_calendar_id, eventId=event_id, body=event)
                .execute()
            )

            return {
                "success": True,
                "message": f"Event '{event_id}' updated successfully.",
                "event": updated_event,
            }

        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Event '{event_id}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to update event: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error updating event: {e}",
                "error": str(e),
            }