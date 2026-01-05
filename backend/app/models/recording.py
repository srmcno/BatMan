"""Recording and Classification models for audio analysis data."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Site
    from app.models.species import Species


class ProcessingStatus(str, Enum):
    """Recording processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VettingStatus(str, Enum):
    """Classification vetting status."""

    AUTO_ACCEPTED = "auto_accepted"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class ActivityType(str, Enum):
    """Bat activity type classification."""

    COMMUTING = "commuting"
    FORAGING = "foraging"
    FEEDING_BUZZ = "feeding_buzz"
    SOCIAL = "social"
    DRINKING = "drinking"
    UNKNOWN = "unknown"


class Recording(Base):
    """Audio recording model."""

    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False
    )

    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256

    # Audio properties
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    channels: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bit_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Recording metadata
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Processing
    status: Mapped[ProcessingStatus] = mapped_column(
        SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Quality metrics
    snr_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    noise_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Detection summary
    total_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feeding_buzzes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Spectrogram paths
    spectrogram_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    spectrogram_thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Additional metadata
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="recordings")
    classifications: Mapped[list["Classification"]] = relationship(
        "Classification", back_populates="recording", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Recording {self.filename}>"


class Classification(Base):
    """Species classification result for a detected call."""

    __tablename__ = "classifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recording_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recordings.id"), nullable=False
    )
    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("species.id"), nullable=False
    )

    # Call timing within recording
    start_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    end_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)

    # Classification confidence
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Alternative predictions
    alternatives: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Activity classification
    activity_type: Mapped[ActivityType] = mapped_column(
        SQLEnum(ActivityType), default=ActivityType.UNKNOWN, nullable=False
    )
    activity_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Vetting
    vetting_status: Mapped[VettingStatus] = mapped_column(
        SQLEnum(VettingStatus), default=VettingStatus.PENDING_REVIEW, nullable=False
    )
    vetted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    vetted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    corrected_species_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("species.id"), nullable=True
    )
    vetting_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Explainable AI data
    xai_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    attention_map_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Call spectrogram
    call_spectrogram_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    recording: Mapped["Recording"] = relationship("Recording", back_populates="classifications")
    species: Mapped["Species"] = relationship("Species", foreign_keys=[species_id])
    corrected_species: Mapped["Species | None"] = relationship(
        "Species", foreign_keys=[corrected_species_id]
    )
    call_parameters: Mapped["CallParameter | None"] = relationship(
        "CallParameter", back_populates="classification", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def final_species_id(self) -> uuid.UUID:
        """Get the final species ID (corrected if available)."""
        return self.corrected_species_id or self.species_id

    def __repr__(self) -> str:
        return f"<Classification {self.species_id} ({self.confidence:.2%})>"


class CallParameter(Base):
    """Measured call parameters for explainable AI."""

    __tablename__ = "call_parameters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    classification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classifications.id"), unique=True, nullable=False
    )

    # Frequency parameters (kHz)
    fc_khz: Mapped[float | None] = mapped_column(Float, nullable=True)  # Characteristic frequency
    fmax_khz: Mapped[float | None] = mapped_column(Float, nullable=True)  # Maximum frequency
    fmin_khz: Mapped[float | None] = mapped_column(Float, nullable=True)  # Minimum frequency
    fmean_khz: Mapped[float | None] = mapped_column(Float, nullable=True)  # Mean frequency
    fknee_khz: Mapped[float | None] = mapped_column(Float, nullable=True)  # Knee frequency
    bandwidth_khz: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Temporal parameters
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_ms: Mapped[float | None] = mapped_column(Float, nullable=True)  # Inter-pulse interval

    # Slope parameters
    slope_khz_per_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    slope_oct_per_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Energy parameters
    peak_amplitude_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_energy_db: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Shape parameters
    curvature: Mapped[float | None] = mapped_column(Float, nullable=True)
    smoothness: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Expected ranges (for XAI comparison)
    expected_ranges: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Feature importance (SHAP values)
    feature_importance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationship
    classification: Mapped["Classification"] = relationship(
        "Classification", back_populates="call_parameters"
    )

    def __repr__(self) -> str:
        return f"<CallParameter fc={self.fc_khz}kHz>"
