"""
Authentication and session management utilities.
"""
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings

# In-memory session store (replace with Redis or database in production)
_sessions: Dict[str, Dict[str, Any]] = {}

class JWTBearer(HTTPBearer):
    """JWT Bearer token authentication."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> str:
        """Validate JWT token from request."""
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code."
            )
        
        if credentials.scheme != "Bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication scheme."
            )
        
        token = credentials.credentials
        if not verify_token(token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired token."
            )
        
        return token

def create_session(user_id: str, user_data: Optional[Dict] = None) -> str:
    """
    Create a new session for a user.
    
    Args:
        user_id: Unique user identifier
        user_data: Additional user data to store in the session
        
    Returns:
        str: Session token
    """
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    
    # Set session expiration time
    expires_at = datetime.utcnow() + timedelta(seconds=settings.SESSION_LIFETIME)
    
    # Store session data
    _sessions[token] = {
        'user_id': user_id,
        'created_at': datetime.utcnow().isoformat(),
        'expires_at': expires_at.isoformat(),
        'last_activity': datetime.utcnow().isoformat(),
        'user_agent': None,
        'ip_address': None,
        'data': user_data or {}
    }
    
    return token

def verify_token(token: str) -> bool:
    """
    Verify if a session token is valid.
    
    Args:
        token: Session token to verify
        
    Returns:
        bool: True if token is valid, False otherwise
    """
    if token not in _sessions:
        return False
    
    session = _sessions[token]
    expires_at = datetime.fromisoformat(session['expires_at'])
    
    # Check if session has expired
    if datetime.utcnow() > expires_at:
        # Clean up expired session
        del _sessions[token]
        return False
    
    # Update last activity
    session['last_activity'] = datetime.utcnow().isoformat()
    
    return True

def get_session(token: str) -> Optional[Dict]:
    """
    Get session data for a token.
    
    Args:
        token: Session token
        
    Returns:
        Optional[Dict]: Session data if valid, None otherwise
    """
    if not verify_token(token):
        return None
    
    return _sessions.get(token)

def revoke_token(token: str) -> None:
    """
    Revoke a session token.
    
    Args:
        token: Session token to revoke
    """
    if token in _sessions:
        del _sessions[token]

def cleanup_expired_sessions() -> int:
    """
    Clean up expired sessions.
    
    Returns:
        int: Number of sessions removed
    """
    expired = []
    now = datetime.utcnow()
    
    for token, session in _sessions.items():
        expires_at = datetime.fromisoformat(session['expires_at'])
        if now > expires_at:
            expired.append(token)
    
    for token in expired:
        del _sessions[token]
    
    return len(expired)

# Start a background task to clean up expired sessions
import asyncio
async def session_cleanup_task():
    """Background task to clean up expired sessions."""
    while True:
        try:
            removed = cleanup_expired_sessions()
            if removed > 0:
                print(f"Cleaned up {removed} expired sessions")
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
        
        # Run cleanup every hour
        await asyncio.sleep(3600)

# Start the cleanup task when the module loads
if __name__ != "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(session_cleanup_task())
