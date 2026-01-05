"""Classification routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.project import Project, Site
from app.models.recording import Classification, Recording, VettingStatus
from app.models.species import Species
from app.models.user import User
from app.api.routes.auth import get_current_active_user
from app.api.schemas import (
    CallParameterResponse,
    ClassificationResponse,
    ClassificationVet,
    PaginatedResponse,
    XAIExplanation,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_classifications(
    recording_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    species_id: uuid.UUID | None = None,
    vetting_status: str | None = None,
    min_confidence: float | None = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List classifications with filters."""
    query = (
        select(Classification)
        .join(Recording)
        .join(Site)
        .join(Project)
        .where(Project.owner_id == current_user.id)
    )

    if recording_id:
        query = query.where(Classification.recording_id == recording_id)
    if site_id:
        query = query.where(Recording.site_id == site_id)
    if species_id:
        query = query.where(Classification.species_id == species_id)
    if vetting_status:
        query = query.where(Classification.vetting_status == vetting_status)
    if min_confidence is not None:
        query = query.where(Classification.confidence >= min_confidence)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results with species info
    query = query.options(selectinload(Classification.species))
    query = query.order_by(Classification.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    classifications = result.scalars().all()

    items = []
    for c in classifications:
        item = ClassificationResponse.model_validate(c)
        if c.species:
            item.species_code = c.species.species_code
            item.species_name = c.species.common_name
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/pending-review", response_model=PaginatedResponse)
async def get_pending_review(
    site_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get classifications pending human review."""
    query = (
        select(Classification)
        .join(Recording)
        .join(Site)
        .join(Project)
        .where(
            Project.owner_id == current_user.id,
            Classification.vetting_status == VettingStatus.PENDING_REVIEW,
        )
        .options(selectinload(Classification.species))
    )

    if site_id:
        query = query.where(Recording.site_id == site_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Order by confidence (lowest first for review)
    query = query.order_by(Classification.confidence.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    classifications = result.scalars().all()

    items = []
    for c in classifications:
        item = ClassificationResponse.model_validate(c)
        if c.species:
            item.species_code = c.species.species_code
            item.species_name = c.species.common_name
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{classification_id}", response_model=ClassificationResponse)
async def get_classification(
    classification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific classification."""
    result = await db.execute(
        select(Classification)
        .join(Recording)
        .join(Site)
        .join(Project)
        .where(
            Classification.id == classification_id,
            Project.owner_id == current_user.id,
        )
        .options(selectinload(Classification.species))
    )
    classification = result.scalar_one_or_none()

    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    response = ClassificationResponse.model_validate(classification)
    if classification.species:
        response.species_code = classification.species.species_code
        response.species_name = classification.species.common_name

    return response


@router.post("/{classification_id}/vet", response_model=ClassificationResponse)
async def vet_classification(
    classification_id: uuid.UUID,
    vet_data: ClassificationVet,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Vet (approve/reject/correct) a classification."""
    result = await db.execute(
        select(Classification)
        .join(Recording)
        .join(Site)
        .join(Project)
        .where(
            Classification.id == classification_id,
            Project.owner_id == current_user.id,
        )
        .options(selectinload(Classification.species))
    )
    classification = result.scalar_one_or_none()

    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    # Update vetting status
    if vet_data.action == "approve":
        classification.vetting_status = VettingStatus.APPROVED
    elif vet_data.action == "reject":
        classification.vetting_status = VettingStatus.REJECTED
    elif vet_data.action == "correct":
        if not vet_data.corrected_species_id:
            raise HTTPException(
                status_code=400,
                detail="corrected_species_id required for correction",
            )
        # Verify species exists
        species = await db.get(Species, vet_data.corrected_species_id)
        if not species:
            raise HTTPException(status_code=404, detail="Species not found")

        classification.vetting_status = VettingStatus.CORRECTED
        classification.corrected_species_id = vet_data.corrected_species_id

    classification.vetted_by_id = current_user.id
    classification.vetted_at = datetime.utcnow()
    classification.vetting_notes = vet_data.notes

    await db.commit()
    await db.refresh(classification)

    response = ClassificationResponse.model_validate(classification)
    if classification.species:
        response.species_code = classification.species.species_code
        response.species_name = classification.species.common_name

    return response


@router.get("/{classification_id}/explain", response_model=XAIExplanation)
async def get_classification_explanation(
    classification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get XAI explanation for a classification."""
    result = await db.execute(
        select(Classification)
        .join(Recording)
        .join(Site)
        .join(Project)
        .where(
            Classification.id == classification_id,
            Project.owner_id == current_user.id,
        )
        .options(
            selectinload(Classification.species),
            selectinload(Classification.call_parameters),
        )
    )
    classification = result.scalar_one_or_none()

    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    # Build explanation
    call_params = None
    if classification.call_parameters:
        call_params = CallParameterResponse.model_validate(classification.call_parameters)

    # Get similar species from alternatives
    similar_species = []
    if classification.alternatives:
        for alt in classification.alternatives.get("species", [])[:5]:
            similar_species.append({
                "species_id": alt.get("id"),
                "species_code": alt.get("code"),
                "species_name": alt.get("name"),
                "similarity": alt.get("confidence", 0),
            })

    # Confidence breakdown from XAI data
    confidence_breakdown = {}
    if classification.xai_data:
        confidence_breakdown = classification.xai_data.get("confidence_breakdown", {})

    return XAIExplanation(
        classification_id=classification.id,
        species_code=classification.species.species_code if classification.species else "",
        species_name=classification.species.common_name if classification.species else "",
        confidence=classification.confidence,
        call_parameters=call_params,
        attention_map_url=classification.attention_map_path,
        similar_species=similar_species,
        confidence_breakdown=confidence_breakdown,
    )


@router.get("/{classification_id}/parameters", response_model=CallParameterResponse)
async def get_call_parameters(
    classification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get measured call parameters for a classification."""
    result = await db.execute(
        select(Classification)
        .join(Recording)
        .join(Site)
        .join(Project)
        .where(
            Classification.id == classification_id,
            Project.owner_id == current_user.id,
        )
        .options(selectinload(Classification.call_parameters))
    )
    classification = result.scalar_one_or_none()

    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    if not classification.call_parameters:
        raise HTTPException(status_code=404, detail="Call parameters not available")

    return CallParameterResponse.model_validate(classification.call_parameters)
