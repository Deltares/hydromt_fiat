"""Settings for the exposure (file(s))."""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from hydromt_fiat.settings.file import InputFileModel
from hydromt_fiat.utils import EXPOSURE__GRID__TYPE

__all__ = ["ExposureGeometry", "ExposureGrid"]


class ExposureGeometrySettings(BaseModel):
    """Settings for reading the exposure geometry data."""

    model_config = ConfigDict(extra="forbid")

    crs: str | None = Field(
        default=None,
        description="Spatial reference system of the file.",
    )


class ExposureGeometry(InputFileModel):
    """Exposure geometry settings for the FIAT model."""

    area_method: str = Field(
        default="centroid",
        description="The method of extracting hazard values \
based on the exposure geometry.",
    )

    impact_type: list[str] = Field(
        default=["damage"],
        description="The impact types to be run for this exposure data.",
    )

    settings: ExposureGeometrySettings | None = Field(
        default=None,
        description="Settings for reading the exposure geometry data.",
    )

    zonal_method: str = Field(
        default="mean",
        description="The zonal statistics method. Only really applicable \
if `area_method` is set to 'area'.",
    )


class ExposureGridSettings(BaseModel):
    """Settings for reading the exposure grid data."""

    model_config = ConfigDict(extra="forbid")

    crs: str | None = Field(
        default=None,
        description="Spatial reference system of the file.",
    )


class ExposureGrid(InputFileModel):
    """Exposure grid settings for the FIAT model."""

    type: str = Field(
        default="default",
        description="The type of the gridded exposure data.",
    )

    resalg: str = Field(
        default="nearest",
        description="Resampling method when reprojecting.",
    )

    settings: ExposureGridSettings | None = Field(
        default=None,
        description="Settings for reading the exposure grid data.",
    )

    # Validator(s)
    @field_validator("type", mode="after")
    @classmethod
    def validate_type(cls, value: str):
        """Validate the exposure grid type."""
        if value not in EXPOSURE__GRID__TYPE:
            raise ValueError(
                f"Exposure grid type invalid: {value}, \
chose from {EXPOSURE__GRID__TYPE}",
            )
        return value
