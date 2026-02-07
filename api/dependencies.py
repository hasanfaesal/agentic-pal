"""
FastAPI dependencies for authentication, session management, and agent access.

This module provides reusable dependencies for:
- Getting the current authenticated user
- Building Google API services with user credentials
- Creating the LangGraph agent with user's services
"""

import secrets
from typing import Annotated, Optional

from fastapi import Cookie, Depends, HTTPException
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from api.session import (
    create_redis_checkpointer,
    get_session_manager,
    SessionManager,
    UserSession,
)


# =============================================================================
# Session Dependencies
# =============================================================================


async def get_session_manager_dep() -> SessionManager:
    """Dependency to get the session manager instance."""
    manager = get_session_manager()
    await manager.connect()
    return manager


async def get_current_session(
    session_manager: Annotated[SessionManager, Depends(get_session_manager_dep)],
    session_id: Optional[str] = Cookie(None)
) -> UserSession:
    """
    Get the current user session.
    
    Raises HTTPException 401 if no valid session exists.
    """
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "no_session",
                "message": "Authentication required. Please log in."
            }
        )
    
    session = await session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "session_expired",
                "message": "Session has expired. Please log in again."
            }
        )
    
    return session


async def get_optional_session(
    session_manager: Annotated[SessionManager, Depends(get_session_manager_dep)],
    session_id: Optional[str] = Cookie(None)
) -> Optional[UserSession]:
    """
    Get the current session if it exists, otherwise return None.
    
    Use this for endpoints that can work with or without authentication.
    """
    if not session_id:
        return None
    
    return await session_manager.get_session(session_id)


# =============================================================================
# Credentials Dependencies
# =============================================================================


async def get_google_credentials(
    session_manager: Annotated[SessionManager, Depends(get_session_manager_dep)],
    session: Annotated[UserSession, Depends(get_current_session)]
) -> Credentials:
    """
    Get valid Google OAuth credentials for the current user.
    
    Automatically refreshes expired tokens if possible.
    Raises HTTPException 401 if credentials are missing or invalid.
    """
    credentials = await session_manager.get_credentials(session.session_id)
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "no_credentials",
                "message": "Google account not connected. Please log in."
            }
        )
    
    # Refresh if expired
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(GoogleAuthRequest())
            await session_manager.store_credentials(
                session_id=session.session_id,
                credentials=credentials,
                user_email=session.user_email
            )
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "credentials_expired",
                    "message": "Google credentials expired. Please log in again."
                }
            )
    
    if not credentials.valid:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_credentials",
                "message": "Google credentials are invalid. Please log in again."
            }
        )
    
    return credentials


# =============================================================================
# Google Services Dependencies
# =============================================================================


def get_calendar_service(
    credentials: Annotated[Credentials, Depends(get_google_credentials)]
):
    """Build Calendar API service with user credentials."""
    from services.calendar import CalendarService
    
    google_service = build("calendar", "v3", credentials=credentials)
    return CalendarService(google_service)


def get_gmail_service(
    credentials: Annotated[Credentials, Depends(get_google_credentials)]
):
    """Build Gmail API service with user credentials."""
    from services.gmail import GmailService
    
    google_service = build("gmail", "v1", credentials=credentials)
    return GmailService(google_service)


def get_tasks_service(
    credentials: Annotated[Credentials, Depends(get_google_credentials)]
):
    """Build Tasks API service with user credentials."""
    from services.tasks import TasksService
    
    google_service = build("tasks", "v1", credentials=credentials)
    return TasksService(google_service)


# =============================================================================
# Agent Dependencies
# =============================================================================


async def get_agent_graph(
    credentials: Annotated[Credentials, Depends(get_google_credentials)]
):
    """
    Create the LangGraph agent with user's Google services.
    
    Returns the compiled graph ready for invocation.
    """
    from services.calendar import CalendarService
    from services.gmail import GmailService
    from services.tasks import TasksService
    from agent.graph.graph_builder import create_graph_runner
    
    # Build services with user credentials
    calendar_service = CalendarService(
        build("calendar", "v3", credentials=credentials)
    )
    gmail_service = GmailService(
        build("gmail", "v1", credentials=credentials)
    )
    tasks_service = TasksService(
        build("tasks", "v1", credentials=credentials)
    )
    
    # Create checkpointer
    checkpointer = await create_redis_checkpointer()
    
    # Build graph
    graph, tools_registry = create_graph_runner(
        calendar_service=calendar_service,
        gmail_service=gmail_service,
        tasks_service=tasks_service,
        checkpointer=checkpointer
    )
    
    return graph, tools_registry


# =============================================================================
# Thread ID Generation
# =============================================================================


def generate_thread_id() -> str:
    """Generate a unique thread ID for conversation tracking."""
    return f"thread_{secrets.token_urlsafe(16)}"
