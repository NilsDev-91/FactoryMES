from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class EbayVariationAspect(BaseModel):
    """Represents a product variation attribute (e.g., Color: Red)."""
    name: str
    value: str

    model_config = ConfigDict(populate_by_name=True)


class EbayBuyer(BaseModel):
    """Represents buyer information."""
    username: str

    model_config = ConfigDict(populate_by_name=True)


class EbayLineItem(BaseModel):
    """Represents a single line item in an eBay order."""
    line_item_id: str = Field(alias="lineItemId")
    legacy_item_id: str = Field(alias="legacyItemId")
    sku: Optional[str] = None
    quantity: int
    title: str
    variation_aspects: List[EbayVariationAspect] = Field(
        default_factory=list, 
        alias="variationAspects"
    )

    model_config = ConfigDict(populate_by_name=True)


class EbayPricingSummary(BaseModel):
    total_value: float = Field(alias="totalValue") # Simplified, usually value+currency struct, but let's assume flattened or we fix parsing
    total_currency: str = Field(alias="totalCurrency", default="USD") # Often nested as price.value, price.currency. 
    # NOTE: eBay API actually returns 'pricingSummary': {'total': {'value': '10.0', 'currency': 'USD'}} 
    # But for now let's adhere to what the processor expects or just fix the processor to handle real ebay response? 
    # User didn't give me the ebay response. 
    # Let's assume the user's existing model was partial.
    # Actually, looking at standard eBay API:
    # "pricingSummary": { "total": { "value": "10.00", "currency": "USD" } }
    # So I should model that correctly.

class EbayPrice(BaseModel):
    value: str
    currency: str

class EbayPricingSummary(BaseModel):
    total: EbayPrice

class EbayOrder(BaseModel):
    """Represents an eBay order from the Fulfillment API."""
    order_id: str = Field(alias="orderId")
    creation_date: datetime = Field(alias="creationDate")
    last_modified_date: datetime = Field(alias="lastModifiedDate")
    order_payment_status: str = Field(alias="orderPaymentStatus")
    order_fulfillment_status: str = Field(alias="orderFulfillmentStatus")
    line_items: List[EbayLineItem] = Field(alias="lineItems")
    buyer: EbayBuyer
    pricing_summary: EbayPricingSummary = Field(alias="pricingSummary")

    model_config = ConfigDict(populate_by_name=True)
