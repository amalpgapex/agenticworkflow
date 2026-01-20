"""
Authentication and authorization dependencies
"""

from fastapi import Header, HTTPException, status
from typing import Optional, Dict, Any
import logging

from app.config import settings
from app.security import EntraIDTokenValidator, SimpleEntraIDTokenValidator

logger = logging.getLogger(__name__)

# Initialize Entra ID validator if configured
_entra_validator = None
if settings.ENTRA_ID_ENABLED and settings.ENTRA_ID_TENANT_ID and settings.ENTRA_ID_CLIENT_ID:
    try:
        if settings.ENTRA_ID_SIMPLE_VALIDATION:
            _entra_validator = SimpleEntraIDTokenValidator(
                tenant_id=settings.ENTRA_ID_TENANT_ID,
                client_id=settings.ENTRA_ID_CLIENT_ID,
                audience=settings.ENTRA_ID_AUDIENCE or settings.ENTRA_ID_CLIENT_ID
            )
            logger.info("Entra ID authentication enabled (simple validation mode)")
        else:
            _entra_validator = EntraIDTokenValidator(
                tenant_id=settings.ENTRA_ID_TENANT_ID,
                client_id=settings.ENTRA_ID_CLIENT_ID,
                audience=settings.ENTRA_ID_AUDIENCE or settings.ENTRA_ID_CLIENT_ID
            )
            logger.info("Entra ID authentication enabled (full RSA verification)")
    except Exception as e:
        logger.warning(f"Failed to initialize Entra ID validator: {e}")
        _entra_validator = None


class CurrentUser:
    """Container for authenticated user information"""
    
    def __init__(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None,
        token_claims: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.given_name = given_name
        self.family_name = family_name
        self.token_claims = token_claims or {}
    
    def __str__(self) -> str:
        return f"{self.email} ({self.user_id})"


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> str:
    """
    Extract and validate the current authenticated user
    
    Priority:
    1. Bearer token from Authorization header (validates with Entra ID if configured)
    2. X-User-Id header (development mode only)
    
    Args:
        authorization: Bearer token from Authorization header
        x_user_id: User ID from custom header (development only)
        
    Returns:
        User ID string
        
    Raises:
        HTTPException: If authentication fails
    """
    
    # Try Entra ID token validation first if configured
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        if _entra_validator:
            try:
                payload = await _entra_validator.validate_token(token)
                user_info = _entra_validator.extract_user_info(payload)
                user_id = user_info.get("user_id")
                if user_id:
                    logger.info(f"Authenticated user via Entra ID: {user_info.get('email')}")
                    return user_id
            except ValueError as e:
                logger.warning(f"Entra ID token validation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {str(e)}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception as e:
                logger.error(f"Unexpected error validating Entra ID token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Token validation error"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Entra ID authentication not configured. Use X-User-Id header for development."
            )
    
    # Development mode: Accept user ID from header
    if x_user_id:
        logger.info(f"Authenticated user via X-User-Id header: {x_user_id}")
        return x_user_id
    
    # No valid authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Bearer token or X-User-Id header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_with_info(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> CurrentUser:
    """
    Extract and validate the current authenticated user with full information
    
    Returns:
        CurrentUser object with detailed user information
        
    Raises:
        HTTPException: If authentication fails
    """
    
    # Try Entra ID token validation first if configured
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        if _entra_validator:
            try:
                payload = await _entra_validator.validate_token(token)
                user_info = _entra_validator.extract_user_info(payload)
                
                return CurrentUser(
                    user_id=user_info.get("user_id"),
                    email=user_info.get("email", ""),
                    name=user_info.get("name"),
                    given_name=user_info.get("given_name"),
                    family_name=user_info.get("family_name"),
                    token_claims=payload
                )
            except ValueError as e:
                logger.warning(f"Entra ID token validation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {str(e)}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception as e:
                logger.error(f"Unexpected error validating Entra ID token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Token validation error"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Entra ID authentication not configured"
            )
    
    # Development mode: Return user ID from header
    if x_user_id:
        return CurrentUser(user_id=x_user_id, email=x_user_id)
    
    # No valid authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Bearer token or X-User-Id header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extract user if authenticated, otherwise return None
    Useful for endpoints that work differently for authenticated vs anonymous users
    
    Returns:
        User ID string or None
    """
    try:
        return await get_current_user(authorization, x_user_id)
    except HTTPException:
        return None
