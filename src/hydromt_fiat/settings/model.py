"""FIAT model settings."""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

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
