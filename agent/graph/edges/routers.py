"""
Conditional edge routing functions.
Determine which node to execute next based on state.
"""

from typing import Literal
from ..state import AgentState


def route_after_planning(state: AgentState) -> Literal["parallel", "sequential", "confirm"]:
    """
    Route to appropriate execution node after planning.
    
    Args:
        state: Current agent state with execution_mode set
        
    Returns:
        Node name to route to
    """
    '''
    Pydantic note: If state is an instance of your Pydantic AgentState, .get() isnt a method on Pydantic models. Prefer attribute access:
    execution_mode = state.execution_mode or "parallel"
    '''
    # Use Pydantic attribute access; default is "parallel" per model
    return state.execution_mode


def route_after_confirm(state: AgentState) -> Literal["execute", "synthesize"]:
    """
    Route after user confirmation.
    
    Args:
        state: Current agent state with user_confirmation processed
        
    Returns:
        "execute" if confirmed, "synthesize" if cancelled
    """
    user_confirmation = (state.user_confirmation or "").lower().strip()
    pending = state.pending_confirmation
    
    # If no pending confirmation, proceed to execute
    if not pending:
        return "execute"
    
    # If user confirmed, execute
    if user_confirmation in ("yes", "y", "confirm", "ok", "proceed"):
        return "execute"
    
    # If user cancelled or unclear, go to synthesize
    return "synthesize"


def should_continue_confirmation(state: AgentState) -> Literal["wait", "proceed", "cancel"]:
    """
    Determine if we should wait for more user input, proceed, or cancel.
    
    Used for the confirmation interrupt loop.
    
    Args:
        state: Current agent state
        
    Returns:
        "wait" to interrupt for user input
        "proceed" to continue execution
        "cancel" to skip to response
    """
    pending = state.pending_confirmation
    user_confirmation = (state.user_confirmation or "").lower().strip()
    
    # No pending confirmation
    if not pending:
        return "proceed"
    
    # User hasn't responded yet
    if not user_confirmation:
        return "wait"
    
    # User confirmed
    if user_confirmation in ("yes", "y", "confirm", "ok", "proceed"):
        return "proceed"
    
    # User cancelled
    if user_confirmation in ("no", "n", "cancel", "abort"):
        return "cancel"
    
    # User wants to edit - wait for more input
    if user_confirmation == "edit":
        return "wait"
    
    # Unclear response - wait for clarification
    return "wait"
