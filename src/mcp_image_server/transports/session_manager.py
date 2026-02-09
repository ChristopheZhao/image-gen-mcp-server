"""
Session management for MCP HTTP server.

This module provides session management functionality including:
- Session creation with secure UUIDs
- Session storage and retrieval (thread-safe)
- Session validation and expiration
- Automatic cleanup of expired sessions
"""

import asyncio
import time
import uuid
from typing import Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Session:
    """Represents an MCP client session."""

    session_id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, timeout: int) -> bool:
        """
        Check if session has expired based on last access time.

        Args:
            timeout: Session timeout in seconds

        Returns:
            bool: True if session has expired
        """
        return (time.time() - self.last_accessed) > timeout

    def update_access_time(self) -> None:
        """Update the last accessed timestamp to current time."""
        self.last_accessed = time.time()

    def age_seconds(self) -> float:
        """Get session age in seconds since creation."""
        return time.time() - self.created_at


class SessionManager:
    """
    Manages MCP client sessions with automatic expiration and cleanup.

    This class is thread-safe and can be used in concurrent environments.
    """

    def __init__(self, timeout: int = 3600, cleanup_interval: int = 300):
        """
        Initialize session manager.

        Args:
            timeout: Session timeout in seconds (default: 1 hour)
            cleanup_interval: Interval between cleanup runs in seconds (default: 5 minutes)
        """
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._timeout = timeout
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """
        Create a new session with a unique ID.

        Args:
            metadata: Optional metadata to store with the session

        Returns:
            Session: The newly created session
        """
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            metadata=metadata or {}
        )

        async with self._lock:
            self._sessions[session_id] = session

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve a session by ID.

        Args:
            session_id: The session ID to retrieve

        Returns:
            Optional[Session]: The session if found and not expired, None otherwise
        """
        async with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                return None

            # Check if session has expired
            if session.is_expired(self._timeout):
                # Remove expired session
                del self._sessions[session_id]
                return None

            return session

    async def update_access_time(self, session_id: str) -> bool:
        """
        Update the last accessed time for a session.

        Args:
            session_id: The session ID to update

        Returns:
            bool: True if session was found and updated, False otherwise
        """
        session = await self.get_session(session_id)
        if session:
            async with self._lock:
                session.update_access_time()
            return True
        return False

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session by ID.

        Args:
            session_id: The session ID to delete

        Returns:
            bool: True if session was found and deleted, False otherwise
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    async def get_session_count(self) -> int:
        """
        Get the current number of active sessions.

        Returns:
            int: Number of active sessions
        """
        async with self._lock:
            return len(self._sessions)

    async def get_all_sessions(self) -> Dict[str, Session]:
        """
        Get all active sessions (for debugging/monitoring).

        Returns:
            Dict[str, Session]: Dictionary of all active sessions
        """
        async with self._lock:
            return self._sessions.copy()

    async def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.

        Returns:
            int: Number of sessions that were cleaned up
        """
        expired_ids = []

        async with self._lock:
            for session_id, session in self._sessions.items():
                if session.is_expired(self._timeout):
                    expired_ids.append(session_id)

            for session_id in expired_ids:
                del self._sessions[session_id]

        return len(expired_ids)

    async def _cleanup_loop(self) -> None:
        """Background task that periodically cleans up expired sessions."""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                cleaned_count = await self.cleanup_expired_sessions()
                if cleaned_count > 0:
                    import sys
                    print(
                        f"Session cleanup: Removed {cleaned_count} expired session(s)",
                        file=sys.stderr
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                import sys
                print(f"Error in session cleanup loop: {e}", file=sys.stderr)

    async def start_cleanup_task(self) -> None:
        """Start the automatic session cleanup background task."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop the automatic session cleanup background task."""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def clear_all(self) -> int:
        """
        Clear all sessions (useful for shutdown or testing).

        Returns:
            int: Number of sessions that were cleared
        """
        async with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count

    def __repr__(self) -> str:
        """String representation of the session manager."""
        return (
            f"SessionManager(timeout={self._timeout}s, "
            f"cleanup_interval={self._cleanup_interval}s, "
            f"active_sessions={len(self._sessions)})"
        )


# Export for convenience
__all__ = ["Session", "SessionManager"]
