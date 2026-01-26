"""
State schema for the agent graph.
Defines the typed state that flows through all nodes.
"""

from typing import List, Optional, Literal, Any, Dict
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


class AgentState(BaseModel):
    """
    State that flows through the agent graph.
    
    All nodes read from and write to this state.
    Uses Pydantic for runtime validation and type safety.
    """
    # Input
    user_message: str
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Classification
    tool_categories: List[str] = Field(default_factory=list)
    
    # Planning
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    requires_confirmation: bool = False
    
    # Execution
    execution_mode: Literal["parallel", "sequential", "confirm"] = "parallel"
    results: Dict[str, Any] = Field(default_factory=dict)
    
    # Confirmation
    pending_confirmation: Optional[Dict[str, Any]] = None
    user_confirmation: Optional[str] = None
    confirmation_message: Optional[str] = None
    
    # Output
    final_response: Optional[str] = None
    
    # Session
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Lazy Loading
    use_lazy_loading: bool = True
    discovered_tools: List[str] = Field(default_factory=list)
    tool_invocations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Error Handling
    error: Optional[str] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # For LangGraph compatibility
        validate_assignment=True,      # Validate on field updates
        frozen=False,                  # Allow mutations
    )
