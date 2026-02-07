"""
Google OAuth2 authentication endpoints for FastAPI.

This module provides:
- /auth/google/login: Initiate OAuth flow
- /auth/google/callback: Handle OAuth callback
- /auth/logout: Clear session and credentials
- /auth/session: Get current session info
"""

import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from api.schemas import (
    ErrorResponse,
    OAuthCallbackResponse,
    OAuthLoginResponse,
    OAuthState,
    SessionInfo,
)
from api.session import get_session_manager, SessionManager


# =============================================================================
# Configuration
# =============================================================================


# OAuth scopes - full access for development
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/userinfo.email",  # Get user email
    "openid",
]


def get_credentials_path() -> Path:
    """Get path to OAuth credentials file."""
    path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    return Path(path).expanduser().resolve()


def get_redirect_uri() -> str:
    """Get OAuth redirect URI."""
    return os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/auth/google/callback"
    )


def get_frontend_url() -> str:
    """Get frontend URL for post-auth redirect."""
    return os.getenv("FRONTEND_URL", "http://localhost:3000")


def get_cookie_domain() -> Optional[str]:
    """Get cookie domain (None for localhost)."""
    return os.getenv("COOKIE_DOMAIN", None)


def is_production() -> bool:
    """Check if running in production mode."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


# =============================================================================
# Router
# =============================================================================


router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# OAuth Flow Helpers
# =============================================================================


def create_oauth_flow(redirect_uri: str) -> Flow:
    """
    Create a Google OAuth2 flow for web applications.
    
    Args:
        redirect_uri: Callback URL for OAuth.
        
    Returns:
        Configured OAuth Flow.
    """
    credentials_path = get_credentials_path()
    
    if not credentials_path.exists():
        raise HTTPException(
            status_code=500,
            detail={
                "error": "configuration_error",
                "message": f"OAuth credentials file not found at {credentials_path}"
            }
        )
    
    return Flow.from_client_secrets_file(
        str(credentials_path),
        scopes=DEFAULT_SCOPES,
        redirect_uri=redirect_uri
    )


async def get_user_email(credentials: Credentials) -> Optional[str]:
    """
    Get user email from Google API using credentials.
    
    Args:
        credentials: Valid Google OAuth credentials.
        
    Returns:
        User's email address or None.
    """
    try:
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info.get("email")
    except Exception:
        return None


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/google/login",
    response_model=OAuthLoginResponse,
    responses={
        200: {"description": "Authorization URL generated successfully"},
        500: {"model": ErrorResponse, "description": "Configuration error"}
    }
)
async def google_login(
    response: Response,
    frontend_redirect: Optional[str] = Query(
        None,
        description="URL to redirect after successful authentication"
    ),
    session_id: Optional[str] = Cookie(None)
):
    """
    Initiate Google OAuth2 login flow.
    
    Returns an authorization URL that the client should redirect to.
    The flow uses CSRF protection via state parameter stored in Redis.
    """
    session_manager = get_session_manager()
    
    # Create or get session
    if session_id:
        session = await session_manager.get_session(session_id)
        if not session:
            session = await session_manager.create_session()
    else:
        session = await session_manager.create_session()
    
    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,
        secure=is_production(),
        samesite="lax",
        domain=get_cookie_domain(),
        max_age=60 * 60 * 24 * 7  # 7 days
    )
    
    # Create OAuth flow
    redirect_uri = get_redirect_uri()
    flow = create_oauth_flow(redirect_uri)
    
    # Generate authorization URL with state for CSRF protection
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"  # Force consent to get refresh token
    )
    
    # Store OAuth state in Redis
    oauth_state = OAuthState(
        state=state,
        redirect_uri=redirect_uri,
        frontend_redirect=frontend_redirect or get_frontend_url()
    )
    await session_manager.store_oauth_state(oauth_state)
    
    return OAuthLoginResponse(authorization_url=authorization_url)


@router.get(
    "/google/callback",
    responses={
        302: {"description": "Redirect to frontend after successful auth"},
        400: {"model": ErrorResponse, "description": "Invalid callback"},
        500: {"model": ErrorResponse, "description": "Server error"}
    }
)
async def google_callback(
    request: Request,
    response: Response,
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="OAuth state for CSRF validation"),
    error: Optional[str] = Query(None, description="Error from Google"),
    session_id: Optional[str] = Cookie(None)
):
    """
    Handle Google OAuth2 callback.
    
    Exchanges the authorization code for tokens, stores credentials in Redis,
    and redirects to the frontend application.
    """
    session_manager = get_session_manager()
    
    # Check for OAuth errors
    if error:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "oauth_error",
                "message": f"Google OAuth error: {error}"
            }
        )
    
    # Validate state (CSRF protection)
    oauth_state = await session_manager.get_oauth_state(state)
    if not oauth_state:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_state",
                "message": "Invalid or expired OAuth state. Please try logging in again."
            }
        )
    
    # Clean up used state
    await session_manager.delete_oauth_state(state)
    
    # Get or create session
    if not session_id:
        session = await session_manager.create_session()
        session_id = session.session_id
    else:
        session = await session_manager.get_session(session_id)
        if not session:
            session = await session_manager.create_session()
            session_id = session.session_id
    
    # Exchange code for tokens
    try:
        flow = create_oauth_flow(oauth_state.redirect_uri)
        flow.fetch_token(code=code)
        credentials = flow.credentials
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "token_exchange_error",
                "message": f"Failed to exchange authorization code: {str(e)}"
            }
        )
    
    # Get user email
    user_email = await get_user_email(credentials)
    
    # Store credentials in Redis
    await session_manager.store_credentials(
        session_id=session_id,
        credentials=credentials,
        user_email=user_email
    )
    
    # Set session cookie
    redirect_response = RedirectResponse(
        url=oauth_state.frontend_redirect or get_frontend_url(),
        status_code=302
    )
    redirect_response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=is_production(),
        samesite="lax",
        domain=get_cookie_domain(),
        max_age=60 * 60 * 24 * 7  # 7 days
    )
    
    return redirect_response


@router.post(
    "/logout",
    responses={
        200: {"description": "Successfully logged out"},
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    }
)
async def logout(
    response: Response,
    session_id: Optional[str] = Cookie(None)
):
    """
    Log out the current user.
    
    Clears the session from Redis and removes the session cookie.
    """
    session_manager = get_session_manager()
    
    if session_id:
        await session_manager.delete_session(session_id)
    
    # Clear cookie
    response.delete_cookie(
        key="session_id",
        httponly=True,
        secure=is_production(),
        samesite="lax",
        domain=get_cookie_domain()
    )
    
    return {"message": "Successfully logged out"}


@router.get(
    "/session",
    response_model=SessionInfo,
    responses={
        200: {"description": "Session information"},
        401: {"model": ErrorResponse, "description": "No active session"}
    }
)
async def get_session_info(
    session_id: Optional[str] = Cookie(None)
):
    """
    Get current session information.
    
    Returns session details including authentication status.
    Does not expose sensitive credential data.
    """
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "no_session",
                "message": "No active session"
            }
        )
    
    session_manager = get_session_manager()
    session = await session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "session_expired",
                "message": "Session has expired. Please log in again."
            }
        )
    
    # Check if credentials exist and are valid
    credentials = await session_manager.get_credentials(session_id)
    authenticated = credentials is not None
    
    # Try to refresh if expired
    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(GoogleAuthRequest())
            await session_manager.store_credentials(
                session_id=session_id,
                credentials=credentials,
                user_email=session.user_email
            )
            authenticated = True
        except Exception:
            authenticated = False
    
    return SessionInfo(
        session_id=session.session_id,
        user_email=session.user_email,
        authenticated=authenticated,
        created_at=session.created_at
    )


@router.post(
    "/refresh",
    responses={
        200: {"description": "Credentials refreshed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        500: {"model": ErrorResponse, "description": "Refresh failed"}
    }
)
async def refresh_credentials(
    session_id: Optional[str] = Cookie(None)
):
    """
    Refresh Google OAuth credentials.
    
    Attempts to refresh the access token using the refresh token.
    """
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "no_session",
                "message": "No active session"
            }
        )
    
    session_manager = get_session_manager()
    session = await session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "session_expired",
                "message": "Session has expired"
            }
        )
    
    credentials = await session_manager.get_credentials(session_id)
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "no_credentials",
                "message": "No credentials found. Please log in."
            }
        )
    
    if not credentials.refresh_token:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "no_refresh_token",
                "message": "No refresh token available. Please log in again."
            }
        )
    
    try:
        credentials.refresh(GoogleAuthRequest())
        await session_manager.store_credentials(
            session_id=session_id,
            credentials=credentials,
            user_email=session.user_email
        )
        return {"message": "Credentials refreshed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "refresh_failed",
                "message": f"Failed to refresh credentials: {str(e)}"
            }
        )
