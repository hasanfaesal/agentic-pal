"""
Confirmation handling nodes.
Manages human-in-the-loop confirmation for destructive actions.
"""

from typing import List
from ..state import AgentState


# Destructive tools that require confirmation
DESTRUCTIVE_TOOLS = {
    "delete_calendar_event": "calendar event",
    "delete_task": "task",
}


def _build_confirmation_message(actions: List[dict]) -> str:
    """
    Build a human-readable confirmation message.
    
    Args:
        actions: List of actions pending confirmation
        
    Returns:
        Confirmation message string
    """
    destructive_actions = [
        a for a in actions 
        if a.get("tool") in DESTRUCTIVE_TOOLS
    ]
    
    if not destructive_actions:
        return None
    
    lines = ["**Confirmation Required**\n"]
    lines.append("The following actions will modify or delete data:\n")
    
    for action in destructive_actions:
        tool = action.get("tool", "")
        args = action.get("args", {})
        item_type = DESTRUCTIVE_TOOLS.get(tool, "item")
        
        # Build description from args
        if "event_id" in args:
            lines.append(f"- Delete {item_type} (ID: {args['event_id']})")
        elif "task_id" in args:
            lines.append(f"- Delete {item_type} (ID: {args['task_id']})")
        else:
            lines.append(f"- Delete {item_type}")
    
    lines.append("\nReply **yes** to confirm, **no** to cancel, or **edit** to modify.")
    
    return "\n".join(lines)


def confirm_actions(state: AgentState) -> AgentState:
    """
    Prepare confirmation state for destructive actions.
    
    This node builds the confirmation message and pauses for user input.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with confirmation_message and pending_confirmation
    """
    actions = state.get("actions", [])
    
    # Find destructive actions
    destructive_actions = [
        a for a in actions 
        if a.get("tool") in DESTRUCTIVE_TOOLS
    ]
    
    if not destructive_actions:
        # No confirmation needed, proceed
        return {
            **state,
            "requires_confirmation": False,
            "pending_confirmation": None,
            "confirmation_message": None,
        }
    
    # Build confirmation message
    confirmation_message = _build_confirmation_message(actions)
    
    return {
        **state,
        "pending_confirmation": destructive_actions,
        "confirmation_message": confirmation_message,
    }


def process_confirmation(state: AgentState) -> AgentState:
    """
    Process user's confirmation response.
    
    Args:
        state: Current agent state with user_confirmation set
        
    Returns:
        Updated state with confirmation processed
    """
    user_confirmation = state.get("user_confirmation", "").lower().strip()
    actions = state.get("actions", [])
    
    if user_confirmation in ("yes", "y", "confirm", "ok", "proceed"):
        # User confirmed - allow all actions to proceed
        return {
            **state,
            "requires_confirmation": False,
            "pending_confirmation": None,
        }
    
    elif user_confirmation in ("no", "n", "cancel", "abort"):
        # User rejected - remove destructive actions
        non_destructive = [
            a for a in actions 
            if a.get("tool") not in DESTRUCTIVE_TOOLS
        ]
        return {
            **state,
            "actions": non_destructive,
            "requires_confirmation": False,
            "pending_confirmation": None,
            "confirmation_message": "Operation cancelled.",
        }
    
    elif user_confirmation == "edit":
        # User wants to modify - keep pending state
        return {
            **state,
            "confirmation_message": "Please specify what you'd like to change.",
        }
    
    else:
        # Unclear response - ask again
        return {
            **state,
            "confirmation_message": "Please reply **yes** to confirm or **no** to cancel.",
        }
