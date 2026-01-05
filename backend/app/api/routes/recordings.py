"""Recording management routes."""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.project import Project, Site
from app.models.recording import ProcessingStatus, Recording
from app.models.user import User
from app.api.routes.auth import get_current_active_user
from app.api.schemas import (
    PaginatedResponse,
    RecordingResponse,
    RecordingUploadResponse,
)

router = APIRouter()

ALLOWED_EXTENSIONS = {".wav", ".wac", ".zc", ".mp3", ".flac"}


async def save_upload_file(upload_file: UploadFile, destination: Path) -> tuple[int, str]:
    """Save uploaded file and return size and hash."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    hasher = hashlib.sha256()
    size = 0

    async with aiofiles.open(destination, "wb") as f:
        while chunk := await upload_file.read(1024 * 1024):  # 1MB chunks
            await f.write(chunk)
            hasher.update(chunk)
            size += len(chunk)

    return size, hasher.hexdigest()


@router.post("/upload", response_model=RecordingUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_recording(
    site_id: uuid.UUID,
    file: UploadFile = File(...),
    recorded_at: datetime | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new audio recording."""
    # Verify site access
    result = await db.execute(
        select(Site)
        .join(Project)
        .where(
            Site.id == site_id,
            Project.owner_id == current_user.id,
        )
    )
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Generate unique filename
    recording_id = uuid.uuid4()
    filename = f"{recording_id}{file_ext}"
    file_path = Path(settings.storage_path) / "recordings" / str(site_id) / filename

    # Save file
    try:
        file_size, file_hash = await save_upload_file(file, file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Get audio metadata (simplified - would use librosa in production)
    duration = 0.0
    sample_rate = settings.sample_rate
    channels = 1

    # Create recording record
    recording = Recording(
        id=recording_id,
        site_id=site_id,
        filename=filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        file_hash=file_hash,
        duration_seconds=duration,
        sample_rate=sample_rate,
        channels=channels,
        recorded_at=recorded_at or datetime.utcnow(),
        latitude=latitude or site.latitude,
        longitude=longitude or site.longitude,
        status=ProcessingStatus.PENDING,
    )

    db.add(recording)

    # Update site statistics
    site.total_recordings += 1

    await db.commit()

    # Queue for processing (would trigger Celery task)
    # process_recording.delay(str(recording_id))

    return RecordingUploadResponse(
        id=recording.id,
        filename=recording.filename,
        status="pending",
        message="Recording uploaded successfully. Processing will begin shortly.",
    )


@router.get("", response_model=PaginatedResponse)
async def list_recordings(
    site_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List recordings for a site."""
    # Verify site access
    result = await db.execute(
        select(Site)
        .join(Project)
        .where(
            Site.id == site_id,
            Project.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Site not found")

    query = select(Recording).where(Recording.site_id == site_id)

    if status:
        query = query.where(Recording.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.order_by(Recording.recorded_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    recordings = result.scalars().all()

    return PaginatedResponse(
        items=[RecordingResponse.model_validate(r) for r in recordings],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific recording."""
    result = await db.execute(
        select(Recording)
        .join(Site)
        .join(Project)
        .where(
            Recording.id == recording_id,
            Project.owner_id == current_user.id,
        )
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    return recording


@router.delete("/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recording(
    recording_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a recording."""
    result = await db.execute(
        select(Recording)
        .join(Site)
        .join(Project)
        .where(
            Recording.id == recording_id,
            Project.owner_id == current_user.id,
        )
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Delete file
    file_path = Path(recording.file_path)
    if file_path.exists():
        file_path.unlink()

    # Update site statistics
    site = await db.get(Site, recording.site_id)
    if site:
        site.total_recordings = max(0, site.total_recordings - 1)
        site.total_calls = max(0, site.total_calls - recording.total_calls)

    await db.delete(recording)
    await db.commit()


@router.post("/{recording_id}/reprocess", response_model=RecordingResponse)
async def reprocess_recording(
    recording_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reprocess a recording."""
    result = await db.execute(
        select(Recording)
        .join(Site)
        .join(Project)
        .where(
            Recording.id == recording_id,
            Project.owner_id == current_user.id,
        )
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Reset status
    recording.status = ProcessingStatus.PENDING
    recording.processing_error = None
    recording.processed_at = None

    await db.commit()

    # Queue for processing
    # process_recording.delay(str(recording_id))

    return recording
