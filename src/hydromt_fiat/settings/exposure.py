"""Settings for the exposure (file(s))."""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from hydromt_fiat.settings.file import InputFileModel


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

    resalg: str = Field(
        default="nearest",
        description="Resampling method when reprojecting.",
    )

    settings: ExposureGridSettings | None = Field(
        default=None,
        description="Settings for reading the exposure grid data.",
    )


class Exposure(BaseModel):
    """Exposure settings for the FIAT model."""

    geom: list[ExposureGeometry] | None = Field(
        default=None,
        description="Exposure geometry settings for the FIAT model.",
    )

    grid: ExposureGrid | None = Field(
        default=None,
        description="Exposure grid settings for the FIAT model.",
    )

    @field_validator("geom", mode="before")
    @classmethod
    def ensure_list(cls, value):
        """Ensure list typing."""
        if not isinstance(value, list):
            value = [value]
        return value

    @property
    def is_empty(self) -> bool:
        """Return whether this entry is empty."""
        return all(value is None for value in self.__dict__.values())
