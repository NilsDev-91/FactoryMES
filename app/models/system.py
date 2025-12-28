from typing import Literal
from pydantic import BaseModel


class EbayConfigUpdate(BaseModel):
    """Model for updating eBay configuration."""
    ebay_app_id: str
    ebay_cert_id: str
    ebay_ru_name: str
    ebay_env: Literal["SANDBOX", "PRODUCTION"]
