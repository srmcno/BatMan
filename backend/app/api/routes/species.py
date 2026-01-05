"""Species routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.species import Species, SpeciesRange
from app.models.user import User
from app.api.routes.auth import get_current_active_user
from app.api.schemas import RegionalSpeciesResponse, SpeciesResponse

router = APIRouter()


@router.get("", response_model=list[SpeciesResponse])
async def list_species(
    family: str | None = None,
    endangered_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all species."""
    query = select(Species)

    if family:
        query = query.where(Species.family == family)
    if endangered_only:
        query = query.where(Species.is_endangered == True)

    query = query.order_by(Species.common_name)
    result = await db.execute(query)
    species = result.scalars().all()

    return [SpeciesResponse.model_validate(s) for s in species]


@router.get("/regional", response_model=RegionalSpeciesResponse)
async def get_regional_species(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    month: int = Query(None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    """Get species expected at a specific location and time."""
    # Get current month if not specified
    if month is None:
        month = datetime.utcnow().month

    # Find species with ranges containing this point
    # Simplified query - production would use PostGIS ST_Contains
    result = await db.execute(
        select(SpeciesRange).where(
            SpeciesRange.min_latitude <= latitude,
            SpeciesRange.max_latitude >= latitude,
            SpeciesRange.min_longitude <= longitude,
            SpeciesRange.max_longitude >= longitude,
        )
    )
    ranges = result.scalars().all()

    species_ids = set()
    for r in ranges:
        # Check seasonal presence
        if r.seasonal_presence and len(r.seasonal_presence) >= month:
            if r.seasonal_presence[month - 1]:
                species_ids.add(r.species_id)
        else:
            species_ids.add(r.species_id)

    # Get species details
    if species_ids:
        result = await db.execute(
            select(Species)
            .where(Species.id.in_(species_ids))
            .order_by(Species.common_name)
        )
        species = result.scalars().all()
    else:
        species = []

    return RegionalSpeciesResponse(
        latitude=latitude,
        longitude=longitude,
        month=month,
        species=[SpeciesResponse.model_validate(s) for s in species],
        total_count=len(species),
    )


@router.get("/{species_id}", response_model=SpeciesResponse)
async def get_species(
    species_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific species."""
    species = await db.get(Species, species_id)

    if not species:
        raise HTTPException(status_code=404, detail="Species not found")

    return SpeciesResponse.model_validate(species)


@router.get("/code/{species_code}", response_model=SpeciesResponse)
async def get_species_by_code(
    species_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a species by its code (e.g., EPFU)."""
    result = await db.execute(
        select(Species).where(Species.species_code == species_code.upper())
    )
    species = result.scalar_one_or_none()

    if not species:
        raise HTTPException(status_code=404, detail="Species not found")

    return SpeciesResponse.model_validate(species)


@router.get("/{species_id}/expected-ranges")
async def get_expected_ranges(
    species_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get expected call parameter ranges for a species."""
    species = await db.get(Species, species_id)

    if not species:
        raise HTTPException(status_code=404, detail="Species not found")

    return species.get_expected_ranges()
