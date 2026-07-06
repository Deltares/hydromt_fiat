"""FIAT model settings."""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from hydromt_fiat.utils import FLOOD_DEPTH, GEOM, GRID, HAZARD


class ModelGeom(BaseModel):
    """Settings for the geometry based model."""

    chunk: int | None = Field(
        default=None, ge=1, description="The chunking size (number of features)."
    )


class ModelGrid(BaseModel):
    """Settings for the grid based model."""

    base: str = Field(
        default=HAZARD,
        description="Which file to take as the base in terms of transform and extend.",
    )

    chunk: list[int, int] | None = Field(
        default=None, description="The chunking size (number of rows and columns)."
    )


class ModelProjection(BaseModel):
    """Settings for the model-wide crs."""

    crs: str = Field(
        default=None, description="The model-wide coordinate reference system."
    )

    force: bool = Field(
        default=False,
        description="Force the model-wide crs on all the spatial input files.",
    )


class Model(BaseModel):
    """Model settings for the FIAT model."""

    geom: ModelGeom | None = Field(
        default=None, description="The model settings specific to the geometry model."
    )

    grid: ModelGrid | None = Field(
        default=None, description="The model settings specific to the grid model."
    )

    loglevel: str = Field(default="INFO", description="The logging level of FIAT.")

    method: str = Field(
        default=FLOOD_DEPTH,
        description="Method to use for the model. \
Can be either 'flood.depth' or 'flood.level'.",
    )

    projection: ModelProjection | None = Field(
        default=None, description="The model wide projection."
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

    type: str = Field(
        default=...,
        description="Type of the model. Can be either 'geom' or 'grid'.",
    )

    @field_validator("type", mode="after")
    @classmethod
    def validate_type(cls, value: str):
        """Check the model type."""
        if value not in [GEOM, GRID]:
            raise ValueError(
                f"Model type should be either {GEOM} or {GRID}, got: {value}",
            )
        return value
