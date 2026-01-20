from datetime import datetime, timedelta
# Date parsing utilities (dateparser is required)
import dateparser


# =============================================================================
# Date/Time Parsing Utilities
# =============================================================================

def parse_datetime(
    date_string: str,
    timezone: str = "UTC",
    default_hour: int = 9,
) -> tuple[str, bool]:
    """
    Parse natural language date/time string to ISO 8601 format.
    
    Args:
        date_string: Natural language date (e.g., "tomorrow at 2pm", "next Tuesday")
        timezone: Timezone for the parsed date
        default_hour: Default hour if no time specified (for events)
        
    Returns:
        Tuple of (ISO formatted datetime string, is_all_day flag)
    """
    if not date_string:
        raise ValueError("Date string cannot be empty")
    
    # Check if it's already in ISO format
    try:
        parsed = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return parsed.isoformat(), False
    except ValueError:
        pass
    
    # Natural-language parsing via dateparser
    settings = {
        "PREFER_DATES_FROM": "future",
        "TIMEZONE": timezone,
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    parsed = dateparser.parse(date_string, settings=settings)
    if not parsed:
        raise ValueError(f"Could not parse date: {date_string}.")

    has_time = any(t in date_string.lower() for t in [
        "am", "pm", ":", "noon", "midnight", "morning", "afternoon", "evening"
    ])
    if not has_time:
        return parsed.strftime("%Y-%m-%d"), True
    return parsed.isoformat(), False


def parse_duration(duration_string: str) -> timedelta:
    """
    Parse duration string to timedelta.
    
    Args:
        duration_string: Duration like "1 hour", "30 minutes", "2h", "1.5 hours"
        
    Returns:
        timedelta object
    """
    duration_string = duration_string.lower().strip()
    
    # Common patterns
    if "hour" in duration_string or duration_string.endswith("h"):
        try:
            hours = float(duration_string.replace("hours", "").replace("hour", "").replace("h", "").strip())
            return timedelta(hours=hours)
        except ValueError:
            pass
    
    if "minute" in duration_string or duration_string.endswith("m"):
        try:
            minutes = float(duration_string.replace("minutes", "").replace("minute", "").replace("min", "").replace("m", "").strip())
            return timedelta(minutes=minutes)
        except ValueError:
            pass
    
    if "day" in duration_string or duration_string.endswith("d"):
        try:
            days = float(duration_string.replace("days", "").replace("day", "").replace("d", "").strip())
            return timedelta(days=days)
        except ValueError:
            pass
    
    # Default to 1 hour if unparseable
    return timedelta(hours=1)


def calculate_end_time(start_time: str, duration: str = "1 hour") -> str:
    """
    Calculate end time from start time and duration.
    
    Args:
        start_time: ISO formatted start time
        duration: Duration string
        
    Returns:
        ISO formatted end time
    """
    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    except ValueError:
        start = dateparser.parse(start_time)
        if not start:
            raise ValueError(f"Could not parse start time: {start_time}")

    delta = parse_duration(duration)
    end = start + delta
    return end.isoformat()

