"""
Pydantic models for API request/response validation.

This module defines the data models used for:
- Chat endpoint requests and responses
- WebSocket streaming events
- OAuth state management
- User session data
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Chat Models
# =============================================================================


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""
    
    user_message: str = Field(
        ...,
        description="The user's message/query to the agent",
        min_length=1,
        max_length=10000,
        examples=["What meetings do I have tomorrow?", "Create a task to review the budget report"]
    )
    thread_id: Optional[str] = Field(
        None,
        description="Optional thread ID for conversation continuity. If not provided, a new thread is created.",
        examples=["thread_abc123"]
    )
    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Optional conversation history for context"
    )


class ActionResult(BaseModel):
    """Result of a single action executed by the agent."""
    
    id: str = Field(..., description="Unique action identifier")
    tool: str = Field(..., description="Name of the tool that was executed")
    success: bool = Field(..., description="Whether the action succeeded")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data from the tool")
    error: Optional[str] = Field(None, description="Error message if the action failed")


class ChatResponse(BaseModel):
    """Response body for the /chat endpoint."""
    
    response: str = Field(
        ...,
        description="The agent's natural language response"
    )
    thread_id: str = Field(
        ...,
        description="Thread ID for conversation continuity"
    )
    actions: List[ActionResult] = Field(
        default_factory=list,
        description="List of actions executed by the agent"
    )
    requires_confirmation: bool = Field(
        False,
        description="Whether the agent is waiting for user confirmation"
    )
    confirmation_message: Optional[str] = Field(
        None,
        description="Message asking for confirmation (if requires_confirmation is True)"
    )


# =============================================================================
# SSE Streaming Models
# =============================================================================


class StreamEventType(str, Enum):
    """Types of events sent over SSE during streaming."""
    
    # Connection events
    CONNECTED = "connected"
    ERROR = "error"
    
    # Streaming events
    TOKEN = "token"
    NODE_START = "node_start"
    NODE_END = "node_end"
    
    # Action events
    ACTION_START = "action_start"
    ACTION_END = "action_end"
    
    # Completion events
    COMPLETE = "complete"
    CONFIRMATION_REQUIRED = "confirmation_required"


class StreamEvent(BaseModel):
    """Event sent over SSE during streaming response."""
    
    event_type: StreamEventType = Field(
        ...,
        description="Type of streaming event"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload data"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp"
    )


class ChatStreamRequest(BaseModel):
    """Request body for /chat/stream endpoint (SSE). DEPRECATED — stream now uses GET with thread_id only."""
    
    user_message: str = Field(
        ...,
        description="The user's message/query to the agent",
        min_length=1,
        max_length=10000,
        examples=["What meetings do I have tomorrow?"]
    )
    thread_id: Optional[str] = Field(
        None,
        description="Optional thread ID for conversation continuity"
    )
    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Optional conversation history for context"
    )


class SendMessageRequest(BaseModel):
    """Request body for POST /chat/message — stores the user's message server-side."""
    
    user_message: str = Field(
        ...,
        description="The user's message/query to the agent",
        min_length=1,
        max_length=10000,
        examples=["What meetings do I have tomorrow?"]
    )
    thread_id: Optional[str] = Field(
        None,
        description="Optional thread ID for conversation continuity. If not provided, a new thread is created."
    )


class SendMessageResponse(BaseModel):
    """Response body for POST /chat/message — confirms message was stored."""
    
    thread_id: str = Field(
        ...,
        description="Thread ID to use when opening the SSE stream"
    )
    status: str = Field(
        default="queued",
        description="Message status (queued for agent processing)"
    )


class ConfirmActionRequest(BaseModel):
    """Request body for /chat/confirm endpoint."""
    
    thread_id: str = Field(
        ...,
        description="Thread ID of the conversation requiring confirmation"
    )


class CancelActionRequest(BaseModel):
    """Request body for /chat/cancel endpoint."""
    
    thread_id: str = Field(
        ...,
        description="Thread ID of the conversation to cancel"
    )


# =============================================================================
# OAuth Models
# =============================================================================


class OAuthState(BaseModel):
    """OAuth state stored in Redis during authorization flow."""
    
    state: str = Field(..., description="OAuth state parameter for CSRF protection")
    redirect_uri: str = Field(..., description="Callback URL for OAuth flow")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the OAuth flow was initiated"
    )
    # Frontend URL to redirect after successful auth
    frontend_redirect: Optional[str] = Field(
        None,
        description="URL to redirect user after successful authentication"
    )


class OAuthLoginResponse(BaseModel):
    """Response for /auth/google/login endpoint."""
    
    authorization_url: str = Field(
        ...,
        description="Google OAuth authorization URL to redirect user to"
    )


class OAuthCallbackResponse(BaseModel):
    """Response for /auth/google/callback endpoint."""
    
    success: bool = Field(..., description="Whether authentication was successful")
    message: str = Field(..., description="Status message")
    user_email: Optional[str] = Field(None, description="Authenticated user's email")


# =============================================================================
# Session Models
# =============================================================================


class UserSession(BaseModel):
    """User session data stored in Redis."""
    
    session_id: str = Field(..., description="Unique session identifier")
    user_email: Optional[str] = Field(None, description="User's email address")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Session creation time"
    )
    last_accessed: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last access time"
    )
    # Google OAuth credentials (serialized)
    credentials: Optional[Dict[str, Any]] = Field(
        None,
        description="Serialized Google OAuth credentials"
    )
    # Active thread IDs for this user
    thread_ids: List[str] = Field(
        default_factory=list,
        description="List of conversation thread IDs"
    )


class SessionInfo(BaseModel):
    """Public session information (no sensitive data)."""
    
    session_id: str = Field(..., description="Session identifier")
    user_email: Optional[str] = Field(None, description="User's email")
    authenticated: bool = Field(..., description="Whether user has valid Google credentials")
    created_at: datetime = Field(..., description="Session creation time")


# =============================================================================
# Error Models
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class RateLimitResponse(BaseModel):
    """Rate limit exceeded response."""
    
    error: str = Field(default="rate_limit_exceeded", description="Error type")
    message: str = Field(..., description="Rate limit message")
    retry_after: int = Field(..., description="Seconds until rate limit resets")


# =============================================================================
# Health Check Models
# =============================================================================


class HealthCheck(BaseModel):
    """Health check response."""
    
    status: str = Field(default="healthy", description="Service status")
    version: str = Field(..., description="API version")
    redis_connected: bool = Field(..., description="Redis connection status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
