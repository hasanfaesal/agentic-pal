"""
FastAPI application for Agentic-PAL LangGraph Agent.

This module provides:
- POST /chat: Synchronous chat endpoint
- WebSocket /chat/ws: Streaming chat with real-time tokens
- CORS configuration for frontend integration
- Rate limiting middleware
- Health check endpoints
"""

import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, Dict, Optional

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api import __version__
from api.auth import router as auth_router
from api.dependencies import (
    generate_thread_id,
    get_agent_graph,
    get_current_session,
    get_google_credentials,
    get_session_manager_dep,
)
from api.schemas import (
    ActionResult,
    CancelActionRequest,
    ChatRequest,
    ChatResponse,
    ChatStreamRequest,
    ConfirmActionRequest,
    ErrorResponse,
    HealthCheck,
    SendMessageRequest,
    SendMessageResponse,
    StreamEvent,
    StreamEventType,
)
from api.session import create_redis_checkpointer, get_session_manager, SessionManager

from api.session import create_redis_checkpointer, get_session_manager, SessionManager
# Configuration
# =============================================================================


def get_allowed_origins() -> list[str]:
    """Get allowed CORS origins from environment or defaults."""
    origins_str = os.getenv("CORS_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",")]
    return [
        "http://localhost:3000",      # React/Vue.js dev server
        "https://app.example.com",    # Production frontend (placeholder)
    ]


def get_rate_limit() -> str:
    """Get rate limit from environment or default."""
    return os.getenv("RATE_LIMIT", "60/minute")


# =============================================================================
# Rate Limiter
# =============================================================================


def get_session_key(request: Request) -> str:
    """
    Get rate limit key from session cookie or IP address.
    
    Uses session_id if available, otherwise falls back to IP.
    """
    session_id = request.cookies.get("session_id")
    if session_id:
        return f"session:{session_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_session_key)


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Connects to Redis on startup, disconnects on shutdown.
    """
    # Startup
    session_manager = get_session_manager()
    await session_manager.connect()
    print(f"🚀 Agentic-PAL API v{__version__} started")
    print(f"📡 Redis connected: {await session_manager.ping()}")
    
    yield
    
    # Shutdown
    await session_manager.disconnect()
    print("👋 Agentic-PAL API shutdown")


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="Agentic-PAL API",
    description="""
    A LangGraph-powered personal assistant API for managing:
    - Google Calendar events
    - Gmail messages
    - Google Tasks
    
    Supports synchronous queries and real-time streaming via Server-Sent Events (SSE).
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# Middleware
# =============================================================================


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# =============================================================================
# Include Routers
# =============================================================================


app.include_router(auth_router)


# =============================================================================
# Health Check Endpoints
# =============================================================================


@app.get(
    "/health",
    response_model=HealthCheck,
    tags=["Health"],
    summary="Health check"
)
async def health_check():
    """
    Check API health status.
    
    Returns service status, version, and Redis connectivity.
    """
    session_manager = get_session_manager()
    redis_connected = await session_manager.ping()
    
    return HealthCheck(
        status="healthy" if redis_connected else "degraded",
        version=__version__,
        redis_connected=redis_connected,
        timestamp=datetime.utcnow()
    )


@app.get(
    "/",
    tags=["Health"],
    summary="API root"
)
async def root():
    """API root - returns basic info."""
    return {
        "name": "Agentic-PAL API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health"
    }


# =============================================================================
# Chat Endpoints
# =============================================================================


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        200: {"description": "Successful response"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Server error"}
    },
    tags=["Chat"],
    summary="Send a chat message (synchronous)"
)
@limiter.limit(get_rate_limit())
async def chat(
    request: Request,
    chat_request: ChatRequest,
    session: Annotated[Any, Depends(get_current_session)],
    graph_and_tools: Annotated[Any, Depends(get_agent_graph)],
):
    """
    Send a message to the agent and receive a complete response.
    
    This endpoint:
    1. Authenticates the user via session cookie (via dependency)
    2. Builds the LangGraph agent with user's Google credentials (via dependency)
    3. Invokes the graph and returns the response
    
    For streaming responses, use the SSE endpoint at POST /chat/stream
    """
    graph, tools_registry = graph_and_tools
    
    # Generate or use provided thread ID
    thread_id = chat_request.thread_id or generate_thread_id()
    
    # Get session manager for tracking
    session_manager = get_session_manager()
    await session_manager.track_thread(session.session_id, thread_id)
    
    # Invoke graph
    try:
        result = await asyncio.to_thread(
            graph.invoke,
            {
                "user_message": chat_request.user_message,
                "conversation_history": chat_request.conversation_history or [],
            },
            {"configurable": {"thread_id": thread_id}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "agent_error", "message": f"Agent error: {str(e)}"}
        )
    
    # Parse actions from results
    actions = []
    if result.get("results"):
        for action_id, action_result in result["results"].items():
            actions.append(ActionResult(
                id=action_id,
                tool=action_result.get("tool", "unknown"),
                success=action_result.get("success", False),
                result=action_result.get("result"),
                error=action_result.get("error")
            ))
    
    return ChatResponse(
        response=result.get("final_response", "I couldn't process your request."),
        thread_id=thread_id,
        actions=actions,
        requires_confirmation=result.get("requires_confirmation", False),
        confirmation_message=result.get("confirmation_message")
    )


# =============================================================================
# Chat Message Endpoint (Step 1: Store message)
# =============================================================================


@app.post(
    "/chat/message",
    response_model=SendMessageResponse,
    responses={
        200: {"description": "Message stored, ready to stream"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Server error"}
    },
    tags=["Chat"],
    summary="Store a user message for streaming (Step 1)"
)
@limiter.limit(get_rate_limit())
async def send_message(
    request: Request,
    msg_request: SendMessageRequest,
    session: Annotated[Any, Depends(get_current_session)],
):
    """
    Store the user's message server-side and return a thread_id.
    
    This is Step 1 of the two-step streaming pattern:
    1. POST /chat/message — stores the message, returns thread_id
    2. GET /chat/stream?thread_id=... — opens SSE, agent processes and streams response
    
    The message is stored in the session manager (Redis) so the stream
    endpoint can retrieve it without the user sending it via URL.
    """
    thread_id = msg_request.thread_id or generate_thread_id()
    
    # Track thread in session
    session_manager = get_session_manager()
    await session_manager.track_thread(session.session_id, thread_id)
    
    # Store the pending message in Redis so /chat/stream can retrieve it
    await session_manager.store_pending_message(thread_id, msg_request.user_message)
    
    return SendMessageResponse(
        thread_id=thread_id,
        status="queued"
    )


# =============================================================================
# SSE Streaming Endpoint (Step 2: Stream response)
# =============================================================================


@app.get(
    "/chat/stream",
    responses={
        200: {"description": "Streaming response with SSE"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Server error"}
    },
    tags=["Chat"],
    summary="Stream chat response (Server-Sent Events)"
)
@limiter.limit(get_rate_limit())
async def chat_stream(
    request: Request,
    thread_id: str,
    session: Annotated[Any, Depends(get_current_session)],
    graph_and_tools: Annotated[Any, Depends(get_agent_graph)],
):
    """
    Stream the agent's response via SSE.
    
    This is Step 2 of the two-step streaming pattern:
    1. POST /chat/message — stores the message, returns thread_id
    2. GET /chat/stream?thread_id=... — opens SSE, agent processes and streams response
    
    The backend retrieves the pending user message from Redis using thread_id.
    Conversation history is reconstructed from backend state (Redis checkpoints).
    No sensitive data is sent via URL — only the thread_id.
    
    Query params:
        thread_id: Thread ID returned by POST /chat/message
    
    Returns: text/event-stream with Server-Sent Events
    """
    graph, tools_registry = graph_and_tools
    
    # Retrieve the pending message from Redis
    session_manager = get_session_manager()
    user_message = await session_manager.get_pending_message(thread_id)
    
    if not user_message:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "no_pending_message",
                "message": "No pending message found for this thread. Send a message via POST /chat/message first."
            }
        )
    
    async def event_generator():
        """Generate SSE events from the agent stream."""
        try:
            # Stream events from graph
            async for event in graph.astream_events(
                {
                    "user_message": user_message,
                    "conversation_history": [],
                },
                {"configurable": {"thread_id": thread_id}},
                version="v2"
            ):
                event_kind = event.get("event", "")
                
                # Node start event
                if event_kind == "on_chain_start":
                    node_name = event.get("name", "")
                    if node_name:
                        stream_event = StreamEvent(
                            event_type=StreamEventType.NODE_START,
                            data={"node": node_name}
                        )
                        yield f"event: {stream_event.event_type}\ndata: {stream_event.model_dump_json()}\n\n"
                
                # Node end event
                elif event_kind == "on_chain_end":
                    node_name = event.get("name", "")
                    if node_name:
                        stream_event = StreamEvent(
                            event_type=StreamEventType.NODE_END,
                            data={"node": node_name}
                        )
                        yield f"event: {stream_event.event_type}\ndata: {stream_event.model_dump_json()}\n\n"
                
                # Token event
                elif event_kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        stream_event = StreamEvent(
                            event_type=StreamEventType.TOKEN,
                            data={"token": chunk.content}
                        )
                        yield f"event: {stream_event.event_type}\ndata: {stream_event.model_dump_json()}\n\n"
            
            # Get final state and send completion
            state = graph.get_state({"configurable": {"thread_id": thread_id}})
            final_response = state.values.get("final_response", "")
            requires_confirmation = state.values.get("requires_confirmation", False)
            
            if requires_confirmation:
                stream_event = StreamEvent(
                    event_type=StreamEventType.CONFIRMATION_REQUIRED,
                    data={
                        "thread_id": thread_id,
                        "message": state.values.get("confirmation_message", ""),
                        "pending_actions": state.values.get("actions", [])
                    }
                )
            else:
                stream_event = StreamEvent(
                    event_type=StreamEventType.COMPLETE,
                    data={
                        "thread_id": thread_id,
                        "response": final_response,
                        "results": state.values.get("results", {})
                    }
                )
            
            yield f"event: {stream_event.event_type}\ndata: {stream_event.model_dump_json()}\n\n"
        
        except Exception as e:
            error_event = StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": "agent_error", "message": str(e)}
            )
            yield f"event: {error_event.event_type}\ndata: {error_event.model_dump_json()}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post(
    "/chat/confirm",
    responses={
        200: {"description": "Actions confirmed and executed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Server error"}
    },
    tags=["Chat"],
    summary="Confirm and execute planned actions"
)
@limiter.limit(get_rate_limit())
async def confirm_action(
    request: Request,
    confirm_request: ConfirmActionRequest,
    session: Annotated[Any, Depends(get_current_session)],
    graph_and_tools: Annotated[Any, Depends(get_agent_graph)],
):
    """
    Confirm and execute the actions that were planned by the agent.
    
    Returns: Final response with execution results
    """
    graph, tools_registry = graph_and_tools
    
    try:
        # Update state with confirmation
        input_state = {
            "actions_confirmed": True,
            "user_confirmation": confirm_request.confirmation
        }
        
        # Run confirmation step
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: graph.invoke(
                input_state,
                {"configurable": {"thread_id": confirm_request.thread_id}}
            )
        )
        
        final_response = result.get("final_response", "")
        results = result.get("results", {})
        
        return {
            "thread_id": confirm_request.thread_id,
            "status": "completed",
            "response": final_response,
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute actions: {str(e)}"
        )


@app.post(
    "/chat/cancel",
    responses={
        200: {"description": "Action cancelled"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Server error"}
    },
    tags=["Chat"],
    summary="Cancel pending action"
)
@limiter.limit(get_rate_limit())
async def cancel_action(
    request: Request,
    cancel_request: CancelActionRequest,
    session: Annotated[Any, Depends(get_current_session)],
    graph_and_tools: Annotated[Any, Depends(get_agent_graph)],
):
    """
    Cancel a pending action that was waiting for user confirmation.
    
    Returns: Confirmation that action was cancelled
    """
    graph, tools_registry = graph_and_tools
    
    try:
        # Update state with cancellation
        input_state = {
            "actions_confirmed": False,
            "user_confirmation": "no"
        }
        
        # Run cancellation step
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: graph.invoke(
                input_state,
                {"configurable": {"thread_id": cancel_request.thread_id}}
            )
        )
        
        return {
            "thread_id": cancel_request.thread_id,
            "status": "cancelled",
            "response": "Action cancelled.",
            "cancelled": True
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel action: {str(e)}"
        )


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler for consistent error format."""
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "message": str(exc.detail)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred"
        }
    )


# =============================================================================
# Run with Uvicorn
# =============================================================================


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT", "development") == "development"
    )
