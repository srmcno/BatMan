"""Project management routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.project import Project, ProjectStatus, Site
from app.models.recording import Recording
from app.models.user import User
from app.api.routes.auth import get_current_active_user
from app.api.schemas import (
    PaginatedResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectSummary,
    ProjectUpdate,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects for the current user."""
    query = select(Project).where(Project.owner_id == current_user.id)

    if status:
        query = query.where(Project.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()

    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    project = Project(
        **project_data.model_dump(),
        owner_id=current_user.id,
        status=ProjectStatus.DRAFT,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()


@router.get("/{project_id}/summary", response_model=ProjectSummary)
async def get_project_summary(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project summary with statistics."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.sites))
        .where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Calculate statistics
    site_count = len(project.sites)
    recording_count = sum(s.total_recordings for s in project.sites)
    total_calls = sum(s.total_calls for s in project.sites)
    species_count = sum(s.species_count for s in project.sites)

    return ProjectSummary(
        id=project.id,
        name=project.name,
        status=project.status.value,
        site_count=site_count,
        recording_count=recording_count,
        total_calls=total_calls,
        species_count=species_count,
    )


# ============================================================================
# Site Routes
# ============================================================================


@router.get("/{project_id}/sites", response_model=list[SiteResponse])
async def list_sites(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all sites for a project."""
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(select(Site).where(Site.project_id == project_id))
    sites = result.scalars().all()

    return [SiteResponse.model_validate(s) for s in sites]


@router.post("/{project_id}/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    project_id: uuid.UUID,
    site_data: SiteCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new site within a project."""
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    site = Site(**site_data.model_dump(), project_id=project_id)
    db.add(site)
    await db.commit()
    await db.refresh(site)

    return site


@router.get("/{project_id}/sites/{site_id}", response_model=SiteResponse)
async def get_site(
    project_id: uuid.UUID,
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific site."""
    result = await db.execute(
        select(Site)
        .join(Project)
        .where(
            Site.id == site_id,
            Site.project_id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    return site


@router.patch("/{project_id}/sites/{site_id}", response_model=SiteResponse)
async def update_site(
    project_id: uuid.UUID,
    site_id: uuid.UUID,
    site_data: SiteUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a site."""
    result = await db.execute(
        select(Site)
        .join(Project)
        .where(
            Site.id == site_id,
            Site.project_id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    update_data = site_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(site, field, value)

    await db.commit()
    await db.refresh(site)

    return site


@router.delete("/{project_id}/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    project_id: uuid.UUID,
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a site."""
    result = await db.execute(
        select(Site)
        .join(Project)
        .where(
            Site.id == site_id,
            Site.project_id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    await db.delete(site)
    await db.commit()
