"""Batch processing routes."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project, Site
from app.models.recording import ProcessingStatus, Recording
from app.models.user import User
from app.api.routes.auth import get_current_active_user
from app.api.schemas import BatchJobCreate, BatchJobStatus

router = APIRouter()

# In-memory job storage (would use Redis in production)
_batch_jobs: dict[str, dict[str, Any]] = {}


@router.post("/process", response_model=BatchJobStatus, status_code=status.HTTP_202_ACCEPTED)
async def start_batch_processing(
    job_data: BatchJobCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Start batch processing for all pending recordings in a project/site."""
    # Verify access
    result = await db.execute(
        select(Site)
        .join(Project)
        .where(
            Site.id == job_data.site_id,
            Site.project_id == job_data.project_id,
            Project.owner_id == current_user.id,
        )
    )
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Count pending recordings
    result = await db.execute(
        select(Recording)
        .where(
            Recording.site_id == job_data.site_id,
            Recording.status == ProcessingStatus.PENDING,
        )
    )
    pending_recordings = result.scalars().all()

    if not pending_recordings:
        raise HTTPException(status_code=400, detail="No pending recordings to process")

    # Create job
    job_id = str(uuid.uuid4())
    _batch_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "total_files": len(pending_recordings),
        "processed_files": 0,
        "failed_files": 0,
        "start_time": datetime.utcnow(),
        "estimated_completion": None,
        "errors": [],
        "site_id": str(job_data.site_id),
        "project_id": str(job_data.project_id),
        "options": job_data.options or {},
    }

    # In production, this would trigger Celery tasks
    # process_batch.delay(job_id, [str(r.id) for r in pending_recordings])

    return BatchJobStatus(
        job_id=job_id,
        status="queued",
        total_files=len(pending_recordings),
        processed_files=0,
        failed_files=0,
        percentage=0.0,
        start_time=_batch_jobs[job_id]["start_time"],
        estimated_completion=None,
        errors=None,
    )


@router.get("/{job_id}", response_model=BatchJobStatus)
async def get_batch_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get the status of a batch processing job."""
    if job_id not in _batch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _batch_jobs[job_id]

    total = job["total_files"]
    processed = job["processed_files"]
    percentage = (processed / total * 100) if total > 0 else 0

    return BatchJobStatus(
        job_id=job_id,
        status=job["status"],
        total_files=total,
        processed_files=processed,
        failed_files=job["failed_files"],
        percentage=round(percentage, 1),
        start_time=job["start_time"],
        estimated_completion=job.get("estimated_completion"),
        errors=job["errors"] if job["errors"] else None,
    )


@router.post("/{job_id}/cancel", response_model=BatchJobStatus)
async def cancel_batch_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Cancel a batch processing job."""
    if job_id not in _batch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _batch_jobs[job_id]

    if job["status"] in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Job already finished")

    job["status"] = "cancelled"

    # In production, would revoke Celery tasks
    # celery_app.control.revoke(job_id, terminate=True)

    return BatchJobStatus(
        job_id=job_id,
        status="cancelled",
        total_files=job["total_files"],
        processed_files=job["processed_files"],
        failed_files=job["failed_files"],
        percentage=round(job["processed_files"] / job["total_files"] * 100, 1),
        start_time=job["start_time"],
        estimated_completion=None,
        errors=job["errors"] if job["errors"] else None,
    )


@router.get("", response_model=list[BatchJobStatus])
async def list_batch_jobs(
    status: str | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
):
    """List recent batch processing jobs."""
    jobs = list(_batch_jobs.values())

    if status:
        jobs = [j for j in jobs if j["status"] == status]

    # Sort by start time, newest first
    jobs.sort(key=lambda j: j["start_time"], reverse=True)

    return [
        BatchJobStatus(
            job_id=j["job_id"],
            status=j["status"],
            total_files=j["total_files"],
            processed_files=j["processed_files"],
            failed_files=j["failed_files"],
            percentage=round(j["processed_files"] / j["total_files"] * 100, 1) if j["total_files"] > 0 else 0,
            start_time=j["start_time"],
            estimated_completion=j.get("estimated_completion"),
            errors=j["errors"] if j["errors"] else None,
        )
        for j in jobs[:limit]
    ]
