"""
Execution routing node.
Determines whether to run tools in parallel, sequential, or with confirmation.
"""

from ..state import AgentState


def route_execution(state: AgentState) -> AgentState:
    """
    Determine execution mode based on action dependencies and confirmation requirements.
    
    Logic:
    - If requires_confirmation → "confirm"
    - If any action has depends_on → "sequential"
    - Otherwise → "parallel"
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with execution_mode
    """
    actions = state.get("actions", [])
    requires_confirmation = state.get("requires_confirmation", False)
    
    # Check if confirmation is needed first
    if requires_confirmation:
        execution_mode = "confirm"
    # Check if any action has dependencies
    elif any(action.get("depends_on") for action in actions):
        execution_mode = "sequential"
    else:
        execution_mode = "parallel"
    
    return {**state, "execution_mode": execution_mode}
