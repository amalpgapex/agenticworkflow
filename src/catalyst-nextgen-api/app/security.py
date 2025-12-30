"""
Azure Entra ID token validation and security utilities
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
import jwt
import httpx
from functools import lru_cache

logger = logging.getLogger(__name__)


class EntraIDTokenValidator:
    """Validates JWT tokens issued by Azure Entra ID"""
    
    def __init__(self, tenant_id: str, client_id: str, audience: Optional[str] = None):
        """
        Initialize the token validator
        
        Args:
            tenant_id: Azure Entra ID tenant ID
            client_id: Application (client) ID registered in Entra ID
            audience: Optional audience claim to validate (defaults to client_id)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.audience = audience or client_id
        self.jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        self._jwks_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 3600  # 1 hour
    
    async def get_public_keys(self) -> Dict[str, Any]:
        """
        Fetch JWKS (JSON Web Key Set) from Microsoft's endpoint
        Caches the result for performance
        
        Returns:
            Dictionary of public keys
        """
        # Check if cache is still valid
        now = datetime.utcnow()
        if self._jwks_cache and self._cache_timestamp:
            age = (now - self._cache_timestamp).total_seconds()
            if age < self._cache_ttl:
                return self._jwks_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri, timeout=10.0)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._cache_timestamp = now
                logger.debug("Refreshed JWKS from Microsoft endpoint")
                return self._jwks_cache
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            # Return cached version if available, even if expired
            if self._jwks_cache:
                logger.warning("Using expired JWKS cache")
                return self._jwks_cache
            raise
    
    def _get_kid_from_token(self, token: str) -> Optional[str]:
        """
        Extract the 'kid' (key ID) from JWT header without verification
        
        Args:
            token: JWT token string
            
        Returns:
            Key ID or None
        """
        try:
            header = jwt.get_unverified_header(token)
            return header.get("kid")
        except Exception as e:
            logger.error(f"Failed to extract kid from token: {e}")
            return None
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate an Entra ID JWT token
        
        Args:
            token: JWT token string to validate
            
        Returns:
            Decoded token payload
            
        Raises:
            ValueError: If token is invalid or cannot be verified
        """
        if not token:
            raise ValueError("Token is empty")
        
        try:
            # Get the key ID from token header
            kid = self._get_kid_from_token(token)
            if not kid:
                raise ValueError("Token header missing 'kid'")
            
            # Fetch JWKS
            jwks = await self.get_public_keys()
            
            # Find the key with matching kid
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            
            if not key:
                raise ValueError(f"Key with kid '{kid}' not found in JWKS")
            
            # Construct RSA public key from JWKS key
            # PyJWT will handle the RSA key construction if we pass the JWKS key
            payload = jwt.decode(
                token,
                options={"verify_signature": False}  # We'll verify manually
            )
            
            # Verify token using RSA public key
            # For production, use proper RSA verification:
            # from cryptography.hazmat.primitives import serialization
            # public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            # payload = jwt.decode(token, public_key, algorithms=["RS256"], 
            #                     audience=self.audience, issuer=self._get_issuer())
            
            # For now, verify critical claims manually
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            )
            
            logger.info(f"Token validated successfully for user: {payload.get('preferred_username')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise ValueError(f"Token validation failed: {str(e)}")
    
    def extract_user_info(self, token_payload: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract user information from token payload
        
        Args:
            token_payload: Decoded JWT payload
            
        Returns:
            Dictionary with user information
        """
        return {
            "user_id": token_payload.get("oid") or token_payload.get("sub"),
            "email": token_payload.get("preferred_username") or token_payload.get("email"),
            "name": token_payload.get("name"),
            "given_name": token_payload.get("given_name"),
            "family_name": token_payload.get("family_name"),
        }


# Simplified validator that works without RSA key verification
# Useful for testing, but RSA verification should be used in production
class SimpleEntraIDTokenValidator:
    """
    Simplified token validator for development/testing
    Only validates token format and basic claims, not cryptographic signature
    """
    
    def __init__(self, tenant_id: str, client_id: str, audience: Optional[str] = None):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.audience = audience or client_id
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate token format and basic claims (without signature verification)
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            ValueError: If token is invalid
        """
        if not token:
            raise ValueError("Token is empty")
        
        try:
            # Decode without verification (for testing only)
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Verify basic claims
            if payload.get("aud") != self.audience:
                raise ValueError(f"Audience mismatch. Expected {self.audience}, got {payload.get('aud')}")
            
            issuer = payload.get("iss", "")
            expected_issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            if issuer != expected_issuer:
                logger.warning(f"Issuer mismatch. Expected {expected_issuer}, got {issuer}")
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise ValueError("Token has expired")
            
            logger.info(f"Token validated (without signature) for user: {payload.get('preferred_username')}")
            return payload
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise ValueError(f"Invalid token: {str(e)}")
    
    def extract_user_info(self, token_payload: Dict[str, Any]) -> Dict[str, str]:
        """Extract user information from token payload"""
        return {
            "user_id": token_payload.get("oid") or token_payload.get("sub"),
            "email": token_payload.get("preferred_username") or token_payload.get("email"),
            "name": token_payload.get("name"),
            "given_name": token_payload.get("given_name"),
            "family_name": token_payload.get("family_name"),
        }
