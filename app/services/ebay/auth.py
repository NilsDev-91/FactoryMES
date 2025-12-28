import time
import base64
import httpx
import logging
from typing import Optional
from pydantic import BaseModel, Field
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class TokenResponse(BaseModel):
    """Pydantic model for eBay OAuth token response."""
    access_token: str
    expires_in: int
    token_type: str
    # eBay might return other fields like refresh_token in different flows, 
    # but for Client Credentials we only need these.

class EbayAuthManager:
    """
    Singleton manager for eBay OAuth 2.0 Client Credentials tokens.
    Handles token caching, expiration checks, and asynchronous refreshing.
    """
    _instance: Optional['EbayAuthManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EbayAuthManager, cls).__new__(cls)
            cls._instance._token = None
            cls._instance._expires_at = 0
        return cls._instance

    @property
    def is_token_valid(self) -> bool:
        """Checks if the cached token is still valid (with a 30s buffer)."""
        return self._token is not None and time.time() < (self._expires_at - 30)

    async def get_access_token(self) -> str:
        """
        Returns a valid access token. 
        If the cached token is missing or expired, it refreshes it.
        """
        if not self.is_token_valid:
            await self._refresh_token()
        
        return self._token

    async def _refresh_token(self):
        """
        Calls eBay OAuth endpoint to get a new Client Credentials token.
        """
        logger.info("Refreshing eBay access token...")
        
        # Prepare Basic Auth header: Base64(AppID:CertID)
        auth_str = f"{settings.EBAY_APP_ID}:{settings.EBAY_CERT_ID}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {b64_auth}"
        }
        
        # Body for Client Credentials Grant
        # Note: Scope is required by eBay for most operations.
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }
        
        token_url = f"{settings.EBAY_API_BASE_URL}/identity/v1/oauth2/token"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, headers=headers, data=data)
                response.raise_for_status()
                
                token_data = TokenResponse(**response.json())
                
                self._token = token_data.access_token
                # Store absolute expiration timestamp
                self._expires_at = time.time() + token_data.expires_in
                
                logger.info(f"Successfully refreshed eBay token. Expires in {token_data.expires_in}s.")
                
            except httpx.HTTPStatusError as e:
                logger.error(f"eBay Auth Failed (HTTP {e.response.status_code}): {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during eBay token refresh: {str(e)}")
                raise

# Singleton instance
ebay_auth = EbayAuthManager()
