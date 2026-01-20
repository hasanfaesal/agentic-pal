from typing import Optional

from ..date_utils import parse_datetime, calculate_end_time


class CalendarToolsMixin:
    """Calendar-related tool implementations."""

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
