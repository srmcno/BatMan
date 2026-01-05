"""Report generation routes."""

import csv
import io
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.project import Project, Site
from app.models.recording import Classification, Recording, VettingStatus
from app.models.species import Species
from app.models.user import User
from app.api.routes.auth import get_current_active_user
from app.api.schemas import ActivitySummary, DiversityMetrics, ReportRequest, ReportResponse

router = APIRouter()


def calculate_shannon_index(counts: list[int]) -> float:
    """Calculate Shannon diversity index."""
    total = sum(counts)
    if total == 0:
        return 0.0

    h = 0.0
    for count in counts:
        if count > 0:
            p = count / total
            h -= p * (p and __import__("math").log(p))
    return h


def calculate_simpson_index(counts: list[int]) -> float:
    """Calculate Simpson diversity index (1 - D)."""
    total = sum(counts)
    if total <= 1:
        return 0.0

    d = sum(n * (n - 1) for n in counts) / (total * (total - 1))
    return 1 - d


@router.get("/diversity/{project_id}", response_model=DiversityMetrics)
async def get_diversity_metrics(
    project_id: uuid.UUID,
    site_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate diversity metrics for a project or site."""
    # Verify project access
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Build query for species counts
    query = (
        select(
            Classification.species_id,
            func.count(Classification.id).label("count"),
        )
        .join(Recording)
        .join(Site)
        .where(
            Site.project_id == project_id,
            Classification.vetting_status.in_([
                VettingStatus.AUTO_ACCEPTED,
                VettingStatus.APPROVED,
                VettingStatus.CORRECTED,
            ]),
        )
        .group_by(Classification.species_id)
    )

    if site_id:
        query = query.where(Recording.site_id == site_id)
    if start_date:
        query = query.where(Recording.recorded_at >= start_date)
    if end_date:
        query = query.where(Recording.recorded_at <= end_date)

    result = await db.execute(query)
    species_counts = {row.species_id: row.count for row in result}

    counts = list(species_counts.values())
    total_detections = sum(counts)
    species_richness = len(counts)

    if species_richness == 0:
        return DiversityMetrics(
            species_richness=0,
            shannon_index=0.0,
            simpson_index=0.0,
            inverse_simpson=0.0,
            pielou_evenness=0.0,
            chao1_estimator=0.0,
            total_detections=0,
            detection_rate=0.0,
            dominance_index=0.0,
        )

    shannon = calculate_shannon_index(counts)
    simpson = calculate_simpson_index(counts)
    inverse_simpson = 1 / (1 - simpson) if simpson < 1 else float("inf")
    pielou = shannon / __import__("math").log(species_richness) if species_richness > 1 else 1.0

    # Chao1 estimator
    singletons = sum(1 for c in counts if c == 1)
    doubletons = sum(1 for c in counts if c == 2)
    if doubletons > 0:
        chao1 = species_richness + (singletons ** 2) / (2 * doubletons)
    else:
        chao1 = species_richness + (singletons * (singletons - 1)) / 2

    # Get survey nights for detection rate
    nights_query = (
        select(func.count(func.distinct(func.date(Recording.recorded_at))))
        .join(Site)
        .where(Site.project_id == project_id)
    )
    if site_id:
        nights_query = nights_query.where(Recording.site_id == site_id)
    survey_nights = await db.scalar(nights_query) or 1

    return DiversityMetrics(
        species_richness=species_richness,
        shannon_index=round(shannon, 4),
        simpson_index=round(simpson, 4),
        inverse_simpson=round(inverse_simpson, 4),
        pielou_evenness=round(pielou, 4),
        chao1_estimator=round(chao1, 2),
        total_detections=total_detections,
        detection_rate=round(total_detections / survey_nights, 2),
        dominance_index=round(max(counts) / total_detections, 4) if total_detections > 0 else 0.0,
    )


@router.get("/activity/{project_id}", response_model=list[ActivitySummary])
async def get_activity_summary(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get activity summary for all sites in a project."""
    # Verify project access
    result = await db.execute(
        select(Project)
        .where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
        .options(selectinload(Project.sites))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    summaries = []
    for site in project.sites:
        # Get species detected
        species_result = await db.execute(
            select(Species.species_code)
            .join(Classification, Classification.species_id == Species.id)
            .join(Recording)
            .where(Recording.site_id == site.id)
            .distinct()
        )
        species_detected = [row[0] for row in species_result]

        # Get hourly activity
        hourly_result = await db.execute(
            select(
                func.extract("hour", Recording.recorded_at).label("hour"),
                func.sum(Recording.total_calls).label("calls"),
            )
            .where(Recording.site_id == site.id)
            .group_by(func.extract("hour", Recording.recorded_at))
        )
        activity_by_hour = {int(row.hour): int(row.calls) for row in hourly_result}

        # Get daily activity
        daily_result = await db.execute(
            select(
                func.date(Recording.recorded_at).label("date"),
                func.sum(Recording.total_calls).label("calls"),
            )
            .where(Recording.site_id == site.id)
            .group_by(func.date(Recording.recorded_at))
        )
        activity_by_date = {str(row.date): int(row.calls) for row in daily_result}

        summaries.append(
            ActivitySummary(
                site_id=site.id,
                site_name=site.name,
                total_recordings=site.total_recordings,
                total_calls=site.total_calls,
                feeding_buzzes=0,  # Would aggregate from recordings
                species_detected=species_detected,
                activity_by_hour=activity_by_hour,
                activity_by_date=activity_by_date,
            )
        )

    return summaries


@router.get("/export/{project_id}/nabat")
async def export_nabat_csv(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Export data in NABat-compatible CSV format."""
    # Verify project access
    result = await db.execute(
        select(Project)
        .where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
        .options(selectinload(Project.sites))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # NABat header
    writer.writerow([
        "GRTS_Cell_ID",
        "Site_Name",
        "Latitude",
        "Longitude",
        "Survey_Date",
        "Recording_Time",
        "Species_Code",
        "Species_Common",
        "Auto_ID_Confidence",
        "Manual_Vet_Status",
        "Final_ID",
        "Call_Count",
        "Activity_Type",
    ])

    # Get all classifications
    for site in project.sites:
        result = await db.execute(
            select(Classification)
            .join(Recording)
            .where(Recording.site_id == site.id)
            .options(selectinload(Classification.species))
            .order_by(Recording.recorded_at)
        )
        classifications = result.scalars().all()

        for c in classifications:
            recording = await db.get(Recording, c.recording_id)
            final_species = c.corrected_species or c.species

            writer.writerow([
                project.grts_cell_id or "",
                site.name,
                site.latitude,
                site.longitude,
                recording.recorded_at.date().isoformat() if recording else "",
                recording.recorded_at.time().isoformat() if recording else "",
                final_species.species_code if final_species else "",
                final_species.common_name if final_species else "",
                f"{c.confidence:.2%}",
                c.vetting_status.value,
                final_species.species_code if final_species else "",
                1,
                c.activity_type.value,
            ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=nabat_export_{project_id}.csv"
        },
    )


@router.get("/export/{project_id}/summary")
async def export_summary_csv(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Export species summary in CSV format."""
    # Verify project access
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Get species summary
    result = await db.execute(
        select(
            Species.species_code,
            Species.common_name,
            Species.scientific_name,
            func.count(Classification.id).label("total_detections"),
            func.count(func.distinct(func.date(Recording.recorded_at))).label("nights_detected"),
            func.avg(Classification.confidence).label("avg_confidence"),
        )
        .join(Classification, Classification.species_id == Species.id)
        .join(Recording)
        .join(Site)
        .where(Site.project_id == project_id)
        .group_by(Species.id)
        .order_by(func.count(Classification.id).desc())
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Species_Code",
        "Common_Name",
        "Scientific_Name",
        "Total_Detections",
        "Nights_Detected",
        "Avg_Confidence",
    ])

    for row in rows:
        writer.writerow([
            row.species_code,
            row.common_name,
            row.scientific_name,
            row.total_detections,
            row.nights_detected,
            f"{row.avg_confidence:.2%}" if row.avg_confidence else "",
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=species_summary_{project_id}.csv"
        },
    )
