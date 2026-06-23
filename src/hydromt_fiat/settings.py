"""Settings for the Fiat model."""

from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field

from hydromt_fiat.utils import FLOOD_DEPTH


class Geometry(BaseModel):
    """Geometry settings for the Fiat model."""

    file: Path = Field(
        default=...,
        description="Path to the geometry file.",
    )
    crs: str | None = Field(
        default=None,
        description="Coordinate reference system of the geometry.",
    )


class Grid(BaseModel):
    """Grid settings for the Fiat model."""

    file: Path = Field(
        default=...,
        description="Path to the grid file.",
    )
    crs: str | None = Field(
        default=None,
        description="Coordinate reference system of the grid.",
    )
    settings: dict | None = Field(
        default=None,
        description="Additional settings for the grid component.",
    )


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


class Exposure(BaseModel):
    """Exposure settings for the Fiat model."""

    damage_unit: str | None = Field(
        default=None,
        description="Unit of the exposure values.",
    )
    geom: list[Geometry] | None = Field(
        default=None,
        description="Geometry settings for the exposure.",
    )
    grid: Grid | None = Field(
        default=None,
        description="Grid settings for the exposure.",
    )
    # TODO validator only one of geom/grid


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
    # TODO validator only one of geom/grid


class ModelConfig(BaseModel):
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


class Hazard(BaseModel):
    """Hazard settings for the Fiat model."""

    file: Path = Field(
        default=...,
        description="Path to the hazard file.",
    )
    unit: str | None = Field(
        default=None,
        description="Unit of the hazard values.",
    )
    rp: list[float] | None = Field(
        default=None,
        description="Return periods for the hazard values.",
    )
    settings: dict | None = Field(
        default=None,
        description="Additional settings for the hazard component.",
    )


class FiatConfig(BaseModel):
    """Configuration for the Fiat model."""

    name: str = Field(default="fiat", description="Name of the model.")
    model: ModelConfig = Field(
        default=...,
        description="Model settings for the Fiat model.",
    )
    output: Output = Field(
        default=Output(),
        description="Output settings for the model.",
    )
    exposure: Exposure | None = Field(
        default=None,
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

    @staticmethod
    def geom() -> Self:
        """Get the default configuration for the Fiat model."""
        return FiatConfig(
            model=ModelConfig(type="geom"),
            output=Output(geom_name="fiat_geom.geojson"),
            exposure=None,
            vulnerability=None,
        )


geom_model = FiatConfig.geom()
dct = geom_model.model_dump(exclude_none=True)

print(FiatConfig(**dct))

# print(geom_model.model_dump_json(indent=4))
