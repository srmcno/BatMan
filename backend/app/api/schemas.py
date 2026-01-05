"""Pydantic schemas for API request/response validation."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================================================
# Base Schemas
# ============================================================================


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime
    updated_at: datetime


# ============================================================================
# Authentication Schemas
# ============================================================================


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseSchema, TimestampMixin):
    """Schema for user response."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    is_verified: bool


class TokenResponse(BaseModel):
    """Schema for authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ============================================================================
# Project Schemas
# ============================================================================


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    survey_type: str | None = None
    protocol_version: str | None = None
    nabat_project_id: str | None = None
    grts_cell_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    settings: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = None
    description: str | None = None
    status: str | None = None
    survey_type: str | None = None
    protocol_version: str | None = None
    nabat_project_id: str | None = None
    grts_cell_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    settings: dict[str, Any] | None = None


class ProjectResponse(BaseSchema, TimestampMixin):
    """Schema for project response."""

    id: uuid.UUID
    name: str
    description: str | None
    status: str
    owner_id: uuid.UUID
    survey_type: str | None
    protocol_version: str | None
    nabat_project_id: str | None
    grts_cell_id: str | None
    start_date: datetime | None
    end_date: datetime | None
    settings: dict[str, Any] | None


class ProjectSummary(BaseSchema):
    """Schema for project summary with statistics."""

    id: uuid.UUID
    name: str
    status: str
    site_count: int = 0
    recording_count: int = 0
    total_calls: int = 0
    species_count: int = 0


# ============================================================================
# Site Schemas
# ============================================================================


class SiteCreate(BaseModel):
    """Schema for creating a site."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation_m: float | None = None
    habitat_type: str | None = None
    habitat_description: str | None = None
    detector_make: str | None = None
    detector_model: str | None = None
    microphone_type: str | None = None
    metadata: dict[str, Any] | None = None


class SiteUpdate(BaseModel):
    """Schema for updating a site."""

    name: str | None = None
    description: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    elevation_m: float | None = None
    habitat_type: str | None = None
    habitat_description: str | None = None
    detector_make: str | None = None
    detector_model: str | None = None
    microphone_type: str | None = None
    metadata: dict[str, Any] | None = None


class SiteResponse(BaseSchema, TimestampMixin):
    """Schema for site response."""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    latitude: float
    longitude: float
    elevation_m: float | None
    habitat_type: str | None
    habitat_description: str | None
    detector_make: str | None
    detector_model: str | None
    microphone_type: str | None
    total_recordings: int
    total_calls: int
    species_count: int
    metadata: dict[str, Any] | None


# ============================================================================
# Recording Schemas
# ============================================================================


class RecordingResponse(BaseSchema, TimestampMixin):
    """Schema for recording response."""

    id: uuid.UUID
    site_id: uuid.UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    duration_seconds: float
    sample_rate: int
    channels: int
    recorded_at: datetime
    status: str
    snr_db: float | None
    noise_level: str | None
    quality_score: float | None
    total_calls: int
    feeding_buzzes: int
    spectrogram_path: str | None
    spectrogram_thumbnail_path: str | None


class RecordingUploadResponse(BaseModel):
    """Schema for recording upload response."""

    id: uuid.UUID
    filename: str
    status: str
    message: str


# ============================================================================
# Classification Schemas
# ============================================================================


class ClassificationResponse(BaseSchema, TimestampMixin):
    """Schema for classification response."""

    id: uuid.UUID
    recording_id: uuid.UUID
    species_id: uuid.UUID
    species_code: str | None = None
    species_name: str | None = None
    start_time_ms: float
    end_time_ms: float
    duration_ms: float
    confidence: float
    model_version: str
    activity_type: str
    activity_confidence: float | None
    vetting_status: str
    vetted_at: datetime | None
    corrected_species_id: uuid.UUID | None
    vetting_notes: str | None
    call_spectrogram_path: str | None


class ClassificationVet(BaseModel):
    """Schema for vetting a classification."""

    action: str = Field(..., pattern="^(approve|reject|correct)$")
    corrected_species_id: uuid.UUID | None = None
    notes: str | None = None


class CallParameterResponse(BaseSchema):
    """Schema for call parameter response."""

    fc_khz: float | None
    fmax_khz: float | None
    fmin_khz: float | None
    fmean_khz: float | None
    fknee_khz: float | None
    bandwidth_khz: float | None
    duration_ms: float | None
    interval_ms: float | None
    slope_khz_per_ms: float | None
    slope_oct_per_s: float | None
    peak_amplitude_db: float | None
    total_energy_db: float | None
    expected_ranges: dict[str, list[float | None]] | None
    feature_importance: dict[str, float] | None


class XAIExplanation(BaseModel):
    """Schema for XAI explanation response."""

    classification_id: uuid.UUID
    species_code: str
    species_name: str
    confidence: float
    call_parameters: CallParameterResponse | None
    attention_map_url: str | None
    similar_species: list[dict[str, Any]]
    confidence_breakdown: dict[str, float]


# ============================================================================
# Species Schemas
# ============================================================================


class SpeciesResponse(BaseSchema):
    """Schema for species response."""

    id: uuid.UUID
    species_code: str
    scientific_name: str
    common_name: str
    family: str
    genus: str
    iucn_status: str | None
    esa_status: str | None
    is_endangered: bool
    fc_min_khz: float | None
    fc_max_khz: float | None
    fmax_min_khz: float | None
    fmax_max_khz: float | None
    duration_min_ms: float | None
    duration_max_ms: float | None
    call_type: str | None
    description: str | None
    image_url: str | None


class RegionalSpeciesResponse(BaseModel):
    """Schema for regional species list."""

    latitude: float
    longitude: float
    month: int
    species: list[SpeciesResponse]
    total_count: int


# ============================================================================
# Batch Processing Schemas
# ============================================================================


class BatchJobCreate(BaseModel):
    """Schema for creating a batch processing job."""

    project_id: uuid.UUID
    site_id: uuid.UUID
    options: dict[str, Any] | None = None


class BatchJobStatus(BaseModel):
    """Schema for batch job status."""

    job_id: str
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    percentage: float
    start_time: datetime | None
    estimated_completion: datetime | None
    errors: list[dict[str, str]] | None


# ============================================================================
# Report Schemas
# ============================================================================


class ReportRequest(BaseModel):
    """Schema for report generation request."""

    project_id: uuid.UUID
    report_type: str = Field(..., pattern="^(nabat|usfws|custom|summary)$")
    config: dict[str, Any] | None = None


class ReportResponse(BaseModel):
    """Schema for report generation response."""

    report_id: uuid.UUID
    status: str
    download_url: str | None
    expires_at: datetime | None


class DiversityMetrics(BaseModel):
    """Schema for diversity metrics."""

    species_richness: int
    shannon_index: float
    simpson_index: float
    inverse_simpson: float
    pielou_evenness: float
    chao1_estimator: float
    total_detections: int
    detection_rate: float
    dominance_index: float


class ActivitySummary(BaseModel):
    """Schema for activity summary."""

    site_id: uuid.UUID
    site_name: str
    total_recordings: int
    total_calls: int
    feeding_buzzes: int
    species_detected: list[str]
    activity_by_hour: dict[int, int]
    activity_by_date: dict[str, int]


# ============================================================================
# Pagination
# ============================================================================


class PaginatedResponse(BaseModel):
    """Schema for paginated responses."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
