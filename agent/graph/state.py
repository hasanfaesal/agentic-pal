"""
State schema for the agent graph.
Defines the typed state that flows through all nodes.

Uses TypedDict for LangGraph compatibility - allows dictionary-style access
while maintaining type hints for IDE support.
"""

from typing import List, Optional, Literal, Any, Dict, TypedDict
from pydantic import BaseModel, Field, ConfigDict
import uuid


class Action(BaseModel):
    """Represents a single tool action to execute."""
    id: str
    tool: str
    args: Dict[str, Any]
    depends_on: List[str] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(frozen=False)  # Allow mutation of result field


class AgentState(TypedDict, total=False):
    """
    State that flows through the agent graph.
    
    All nodes read from and write to this state.
    Uses TypedDict for LangGraph compatibility - allows dictionary-style
    access (state["key"] and state.get("key", default)).
    
    total=False means all keys are optional by default.
    """
    # Input (required)
    user_message: str
    conversation_history: List[Dict[str, Any]]
    
    # Planning
    actions: List[Dict[str, Any]]
    requires_confirmation: bool
    
    # Execution
    execution_mode: Literal["parallel", "sequential", "confirm"]
    results: Dict[str, Any]
    
    # Confirmation
    pending_confirmation: Optional[Dict[str, Any]]
    user_confirmation: Optional[str]
    confirmation_message: Optional[str]
    
    # Output
    final_response: Optional[str]
    
    # Session
    session_id: str
    session_context: Dict[str, Any]
    
    # Tool Discovery (meta-tools)
    discovered_tools: List[str]
    tool_invocations: List[Dict[str, Any]]
    
    # Error Handling
    error: Optional[str]
    
    # DSPy specific (for debugging)
    _dspy_reasoning: Optional[str]


def create_initial_state(
    user_message: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> AgentState:
    """
    Create an initial agent state with default values.
    
    Args:
        user_message: The user's input message
        conversation_history: Optional conversation history
        
    Returns:
        Initialized AgentState dictionary
    """
    return AgentState(
        user_message=user_message,
        conversation_history=conversation_history or [],
        actions=[],
        requires_confirmation=False,
        execution_mode="parallel",
        results={},
        pending_confirmation=None,
        user_confirmation=None,
        confirmation_message=None,
        final_response=None,
        session_id=str(uuid.uuid4()),
        session_context={},
        discovered_tools=[],
        tool_invocations=[],
        error=None,
    )
