import httpx
import logging
from typing import List
from pydantic import TypeAdapter

from app.core.config import settings
from app.models.ebay import EbayOrder
from app.services.ebay.auth import ebay_auth

logger = logging.getLogger(__name__)

class EbayServiceException(Exception):
    """Custom exception for eBay service errors."""
    pass

class EbayOrderService:
    """
    Service for interacting with the eBay Fulfillment API to manage orders.
    """

    async def fetch_orders(self, limit: int = 50) -> List[EbayOrder]:
        """
        Fetches orders from eBay that are NOT_STARTED or IN_PROGRESS.
        
        Args:
            limit (int): Maximum number of orders to return.
            
        Returns:
            List[EbayOrder]: A list of parsed eBay orders.
            
        Raises:
            EbayServiceException: If there is a network error or API failure.
        """
        try:
            # 1. Get valid access token
            token = await ebay_auth.get_access_token()
            
            # 2. Prepare request
            url = f"{settings.EBAY_API_BASE_URL}/sell/fulfillment/v1/order"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            # Filtering for orders that need processing
            params = {
                "limit": limit,
                "filter": "orderfulfillmentstatus:{NOT_STARTED|IN_PROGRESS}"
            }
            
            # 3. Perform GET request
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"eBay API Error (HTTP {response.status_code}): {response.text}")
                    response.raise_for_status()
                
                data = response.json()
                
                # 4. Parse response
                # The response contains a list of orders in the 'orders' field
                orders_list = data.get("orders", [])
                
                # Use TypeAdapter to validate the list of orders
                adapter = TypeAdapter(List[EbayOrder])
                return adapter.validate_python(orders_list)

        except httpx.HTTPStatusError as e:
            logger.error(f"eBay API Status Error: {str(e)}")
            raise EbayServiceException(f"eBay API failed with status {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"eBay Connectivity Error: {str(e)}")
            raise EbayServiceException("Failed to connect to eBay API") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching eBay orders: {str(e)}")
            raise EbayServiceException(f"An unexpected error occurred: {str(e)}") from e

# Global instance for easy access
ebay_orders = EbayOrderService()
