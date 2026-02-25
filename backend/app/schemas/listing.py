from __future__ import annotations

from pydantic import BaseModel


class ListingResponse(BaseModel):
    id: int
    external_id: str | None = None
    source: str | None = None
    address: str | None = None
    price: float | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    property_type: str | None = None
    description: str | None = None
    neighborhood: str | None = None
    image_url: str | None = None
    year_built: int | None = None
    days_on_market: int | None = None
    listing_url: str | None = None

    model_config = {"from_attributes": True}
