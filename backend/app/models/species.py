"""Species and range models for bat species data."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Species(Base):
    """Bat species model."""

    __tablename__ = "species"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Species identification
    species_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # e.g., EPFU
    scientific_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    common_name: Mapped[str] = mapped_column(String(100), nullable=False)
    family: Mapped[str] = mapped_column(String(100), nullable=False)
    genus: Mapped[str] = mapped_column(String(100), nullable=False)

    # Conservation status
    iucn_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    esa_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_endangered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Call characteristics (typical ranges)
    fc_min_khz: Mapped[float | None] = mapped_column(Float, nullable=True)
    fc_max_khz: Mapped[float | None] = mapped_column(Float, nullable=True)
    fmax_min_khz: Mapped[float | None] = mapped_column(Float, nullable=True)
    fmax_max_khz: Mapped[float | None] = mapped_column(Float, nullable=True)
    fmin_min_khz: Mapped[float | None] = mapped_column(Float, nullable=True)
    fmin_max_khz: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_min_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_max_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    slope_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    slope_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Call type
    call_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # FM, CF, FM-QCF

    # Habitat preferences
    habitat_preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Seasonal presence (1-12 months as boolean array)
    seasonal_presence: Mapped[list[bool] | None] = mapped_column(ARRAY(Boolean), nullable=True)

    # Additional information
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Model training
    training_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def get_expected_ranges(self) -> dict:
        """Get expected parameter ranges for XAI comparison."""
        return {
            "fc_khz": [self.fc_min_khz, self.fc_max_khz],
            "fmax_khz": [self.fmax_min_khz, self.fmax_max_khz],
            "fmin_khz": [self.fmin_min_khz, self.fmin_max_khz],
            "duration_ms": [self.duration_min_ms, self.duration_max_ms],
            "slope": [self.slope_min, self.slope_max],
        }

    def __repr__(self) -> str:
        return f"<Species {self.species_code}: {self.scientific_name}>"


class SpeciesRange(Base):
    """Species geographic range model."""

    __tablename__ = "species_ranges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Geographic bounds (simplified - for full implementation use PostGIS)
    min_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    max_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    min_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    max_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Region identifier
    region_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region_type: Mapped[str] = mapped_column(String(50), nullable=False)  # state, province, country

    # Seasonal presence in this region
    seasonal_presence: Mapped[list[bool] | None] = mapped_column(ARRAY(Boolean), nullable=True)

    # Confidence/data quality
    range_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    data_source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def contains_point(self, latitude: float, longitude: float) -> bool:
        """Check if a point is within this range."""
        return (
            self.min_latitude <= latitude <= self.max_latitude
            and self.min_longitude <= longitude <= self.max_longitude
        )

    def __repr__(self) -> str:
        return f"<SpeciesRange {self.region_name}>"
