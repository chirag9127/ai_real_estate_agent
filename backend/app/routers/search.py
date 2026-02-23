from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.listing import Listing
from app.schemas.listing import ListingResponse
from app.services import search_service

router = APIRouter(prefix="/search")


@router.post("/{requirement_id}", response_model=list[ListingResponse])
async def search_listings(
    requirement_id: int,
    db: Session = Depends(get_db),
) -> list[ListingResponse]:
    listings = await search_service.search_listings(db, requirement_id)
    return [ListingResponse.model_validate(l) for l in listings]


@router.get("/results/{pipeline_run_id}", response_model=list[ListingResponse])
def get_search_results(
    pipeline_run_id: int,
    db: Session = Depends(get_db),
) -> list[ListingResponse]:
    """Get all listings for a given pipeline run."""
    listings = (
        db.query(Listing)
        .filter(Listing.pipeline_run_id == pipeline_run_id)
        .all()
    )
    return [ListingResponse.model_validate(l) for l in listings]
