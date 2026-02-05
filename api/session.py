"""
Redis session management for user authentication and LangGraph checkpoints.

This module provides:
- SessionManager: Manages user sessions with HttpOnly cookies (Redis db=0)
- Credential storage for Google OAuth tokens
- LangGraph checkpoint configuration (Redis db=1)
"""

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import redis.asyncio as redis
from google.oauth2.credentials import Credentials
from pydantic import BaseModel

from api.schemas import OAuthState, UserSession


# =============================================================================
# Configuration
# =============================================================================


def get_redis_url() -> str:
    """Get Redis URL from environment or use default."""
    return os.getenv("REDIS_URL", "redis://localhost:6379")


def get_session_ttl() -> int:
    """Get session TTL in seconds (default: 7 days)."""
    return int(os.getenv("SESSION_TTL_SECONDS", 60 * 60 * 24 * 7))


def get_oauth_state_ttl() -> int:
    """Get OAuth state TTL in seconds (default: 10 minutes)."""
    return int(os.getenv("OAUTH_STATE_TTL_SECONDS", 60 * 10))


def get_session_secret() -> str:
    """Get session secret for cookie signing."""
    secret = os.getenv("SESSION_SECRET")
    if not secret:
        # Generate a random secret if not set (not recommended for production)
        import warnings
        warnings.warn(
            "SESSION_SECRET not set. Using random secret. "
            "This will invalidate sessions on restart.",
            RuntimeWarning
        )
        secret = secrets.token_hex(32)
    return secret


# =============================================================================
# Session Manager
# =============================================================================


class SessionManager:
    """
    Manages user sessions stored in Redis.
    
    Uses Redis db=0 for sessions (short-lived, with TTL).
    Provides methods for:
    - Creating and retrieving sessions
    - Storing Google OAuth credentials
    - Managing OAuth state during authorization flow
    """
    
    SESSION_PREFIX = "session:"
    OAUTH_STATE_PREFIX = "oauth_state:"
    CREDENTIALS_PREFIX = "credentials:"
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize session manager.
        
        Args:
            redis_url: Redis connection URL. Defaults to REDIS_URL env var.
        """
        self.redis_url = redis_url or get_redis_url()
        self._redis: Optional[redis.Redis] = None
        self.session_ttl = get_session_ttl()
        self.oauth_state_ttl = get_oauth_state_ttl()
    
    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                db=0,  # Sessions use db=0
                decode_responses=True
            )
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    async def ping(self) -> bool:
        """Check if Redis is connected and responsive."""
        try:
            await self.connect()
            await self._redis.ping()
            return True
        except Exception:
            return False
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis client, raising if not connected."""
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.SESSION_PREFIX}{session_id}"
    
    async def create_session(self, user_email: Optional[str] = None) -> UserSession:
        """
        Create a new user session.
        
        Args:
            user_email: Optional email address for authenticated user.
            
        Returns:
            New UserSession with generated session_id.
        """
        await self.connect()
        
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        
        session = UserSession(
            session_id=session_id,
            user_email=user_email,
            created_at=now,
            last_accessed=now,
            credentials=None,
            thread_ids=[]
        )
        
        await self.redis.setex(
            self._session_key(session_id),
            self.session_ttl,
            session.model_dump_json()
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            UserSession if found, None otherwise.
        """
        await self.connect()
        
        data = await self.redis.get(self._session_key(session_id))
        if not data:
            return None
        
        session = UserSession.model_validate_json(data)
        
        # Update last accessed time
        session.last_accessed = datetime.utcnow()
        await self.redis.setex(
            self._session_key(session_id),
            self.session_ttl,
            session.model_dump_json()
        )
        
        return session
    
    async def update_session(self, session: UserSession) -> None:
        """
        Update an existing session.
        
        Args:
            session: Updated session data.
        """
        await self.connect()
        
        session.last_accessed = datetime.utcnow()
        await self.redis.setex(
            self._session_key(session.session_id),
            self.session_ttl,
            session.model_dump_json()
        )
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            True if session was deleted, False if not found.
        """
        await self.connect()
        
        result = await self.redis.delete(self._session_key(session_id))
        # Also delete associated credentials
        await self.redis.delete(f"{self.CREDENTIALS_PREFIX}{session_id}")
        
        return result > 0
    
    # =========================================================================
    # Credentials Management
    # =========================================================================
    
    async def store_credentials(
        self,
        session_id: str,
        credentials: Credentials,
        user_email: Optional[str] = None
    ) -> None:
        """
        Store Google OAuth credentials for a session.
        
        Args:
            session_id: Session identifier.
            credentials: Google OAuth credentials.
            user_email: User's email address.
        """
        await self.connect()
        
        # Serialize credentials
        creds_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else [],
        }
        
        # Store credentials with same TTL as session
        await self.redis.setex(
            f"{self.CREDENTIALS_PREFIX}{session_id}",
            self.session_ttl,
            json.dumps(creds_data)
        )
        
        # Update session with email
        session = await self.get_session(session_id)
        if session:
            session.user_email = user_email
            session.credentials = creds_data
            await self.update_session(session)
    
    async def get_credentials(self, session_id: str) -> Optional[Credentials]:
        """
        Retrieve Google OAuth credentials for a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Google Credentials if found, None otherwise.
        """
        await self.connect()
        
        data = await self.redis.get(f"{self.CREDENTIALS_PREFIX}{session_id}")
        if not data:
            return None
        
        creds_data = json.loads(data)
        
        return Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
            scopes=creds_data.get("scopes")
        )
    
    # =========================================================================
    # OAuth State Management
    # =========================================================================
    
    def _oauth_state_key(self, state: str) -> str:
        """Generate Redis key for OAuth state."""
        return f"{self.OAUTH_STATE_PREFIX}{state}"
    
    async def store_oauth_state(self, oauth_state: OAuthState) -> None:
        """
        Store OAuth state during authorization flow.
        
        Args:
            oauth_state: OAuth state data.
        """
        await self.connect()
        
        await self.redis.setex(
            self._oauth_state_key(oauth_state.state),
            self.oauth_state_ttl,
            oauth_state.model_dump_json()
        )
    
    async def get_oauth_state(self, state: str) -> Optional[OAuthState]:
        """
        Retrieve OAuth state.
        
        Args:
            state: OAuth state parameter.
            
        Returns:
            OAuthState if found and not expired, None otherwise.
        """
        await self.connect()
        
        data = await self.redis.get(self._oauth_state_key(state))
        if not data:
            return None
        
        return OAuthState.model_validate_json(data)
    
    async def delete_oauth_state(self, state: str) -> None:
        """
        Delete OAuth state after use.
        
        Args:
            state: OAuth state parameter.
        """
        await self.connect()
        await self.redis.delete(self._oauth_state_key(state))
    
    # =========================================================================
    # Thread Management
    # =========================================================================
    
    async def add_thread_to_session(self, session_id: str, thread_id: str) -> None:
        """
        Add a conversation thread ID to a session.
        
        Args:
            session_id: Session identifier.
            thread_id: Thread identifier to add.
        """
        session = await self.get_session(session_id)
        if session and thread_id not in session.thread_ids:
            session.thread_ids.append(thread_id)
            await self.update_session(session)


# =============================================================================
# LangGraph Checkpoint Configuration
# =============================================================================


def get_checkpoint_redis_url() -> str:
    """
    Get Redis URL for LangGraph checkpoints (db=1).
    
    Returns:
        Redis URL with db=1 for checkpoint storage.
    """
    base_url = get_redis_url()
    # Append db=1 for checkpoints
    if "?" in base_url:
        return f"{base_url}&db=1"
    else:
        return f"{base_url}/1"


async def create_redis_checkpointer():
    """
    Create a Redis-based checkpointer for LangGraph.
    
    Returns:
        AsyncRedisSaver configured for db=1.
    """
    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver
        
        return AsyncRedisSaver.from_conn_string(get_checkpoint_redis_url())
    except ImportError:
        # Fallback to memory saver if redis checkpoint not available
        from langgraph.checkpoint.memory import MemorySaver
        import warnings
        warnings.warn(
            "langgraph-checkpoint-redis not installed. Using MemorySaver. "
            "Install with: pip install langgraph-checkpoint-redis",
            RuntimeWarning
        )
        return MemorySaver()


# =============================================================================
# Global Session Manager Instance
# =============================================================================


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
