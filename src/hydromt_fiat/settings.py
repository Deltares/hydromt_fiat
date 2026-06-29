"""Settings for the Fiat model."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_serializer

from hydromt_fiat.utils import FLOOD_DEPTH, GEOM, GRID


class Model(BaseModel):
    """Model settings for the Fiat model."""

    type: str = Field(
        default=...,
        description="Type of the model. Can be either 'geom' or 'grid'.",
    )
    method: str = Field(
        default=FLOOD_DEPTH,
        description="Method to use for the model. Can be either 'flood.depth' or 'flood.level'.",  # noqa: E501
    )
    risk: bool = Field(
        default=False,
        description="Whether to perform a risk analysis.",
    )
    threads: int = Field(
        default=1,
        ge=1,
        description="Number of threads to use for the model.",
    )

    @field_validator("type", mode="after")
    @classmethod
    def type_check(cls, value: str):
        """Check the model type."""
        if value not in [GEOM, GRID]:
            raise ValueError(
                f"Model type should be either {GEOM} or {GRID}, got: {value}",
            )
        return value


class Geometry(BaseModel):
    """Geometry settings for the Fiat model."""

    file: Path = Field(
        default=...,
        description="Path to the geometry file.",
    )


class Grid(BaseModel):
    """Grid settings for the Fiat model."""

    file: Path = Field(
        default=...,
        description="Path to the grid file.",
    )


class Output(BaseModel):
    """Output settings for the Fiat model."""

    path: Path = Field(
        default=Path("output"),
        description="Directory to store the output of the model.",
    )
    geom: list[Geometry] | None = Field(
        default=None,
        description="Geometry settings for the output.",
    )
    grid: Grid | None = Field(
        default=None,
        description="Name of the output grid file if present.",
    )

    @field_validator("geom", mode="before")
    @classmethod
    def ensure_list(cls, value):
        """Ensure list typing."""
        if not isinstance(value, list):
            value = [value]
        return value


class Vulnerability(BaseModel):
    """Vulnerability settings for the Fiat model."""

    file: Path = Field(
        default=...,
        description="Path to the vulnerability file.",
    )
    settings: dict | None = Field(
        default=None,
        description="Additional settings for the vulnerability component.",
    )


class Hazard(BaseModel):
    """Hazard settings for the Fiat model."""

    file: Path = Field(
        default=...,
        description="Path to the hazard file.",
    )
    rp: list[float] | None = Field(
        default=None,
        description="Return periods for the hazard values.",
    )
    settings: dict | None = Field(
        default=None,
        description="Additional settings for the hazard component.",
    )


class ExposureGeometrySettings(BaseModel):
    """Exposure geometry settings."""

    srs: str = Field(
        default=None,
        description="Spatial reference system of the file.",
    )


class ExposureGeometry(Geometry):
    """Exposure geometry settings."""

    settings: ExposureGeometrySettings | None = Field(
        default=None,
        description="Additional settings for reading the exposure geometry.",
    )


class ExposureGridSettings(BaseModel):
    """Exposure grid settings."""

    srs: str = Field(
        default=None,
        description="Spatial reference system of the file.",
    )


class ExposureGrid(Grid):
    """Grid settings for the Fiat model."""

    settings: ExposureGridSettings | None = Field(
        default=None,
        description="Additional settings for reading the exposure grid.",
    )


class Exposure(BaseModel):
    """Exposure settings for the Fiat model."""

    geom: list[ExposureGeometry] | None = Field(
        default=None,
        description="Geometry settings for the exposure.",
    )
    grid: Grid | None = Field(
        default=None,
        description="Grid settings for the exposure.",
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


class Settings(BaseModel):
    """Configuration for the Fiat model."""

    model: Model = Field(
        default=Model(type="geom"),
        description="FIAT model settings.",
    )
    output: Output = Field(
        default=Output(),
        description="Output settings for the model.",
    )
    exposure: Exposure = Field(
        default=Exposure(),
        description="Exposure settings for the model.",
    )
    vulnerability: Vulnerability | None = Field(
        default=None,
        description="Vulnerability settings for the model.",
    )
    hazard: Hazard | None = Field(
        default=None,
        description="Hazard settings for the model.",
    )

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        """Serialize helper."""
        data = handler(self)
        if self.exposure.is_empty:
            data.pop("exposure", None)
        return data


DEFAULT_SETTINGS = Settings()
