"""Output file settings."""

from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
)

from hydromt_fiat.settings.file import OutputFileModel

__all__ = ["Output"]


class OutputGeometry(OutputFileModel):
    """Geometry model output settings."""


class OutputGrid(OutputFileModel):
    """Geometry model output settings."""


class Output(BaseModel):
    """Output settings for the Fiat model."""

    path: Path = Field(
        default=Path("output"),
        description="Directory to store the output of the model.",
    )

    geom: list[OutputGeometry] | None = Field(
        default=None,
        description="Output settings for the geometry model.",
    )

    grid: OutputGrid | None = Field(
        default=None,
        description="Output settings for the grid model.",
    )

    @field_validator("geom", mode="before")
    @classmethod
    def ensure_list(cls, value):
        """Ensure list typing."""
        if not isinstance(value, list):
            value = [value]
        return value

    @field_serializer("path")
    def serialize_path(self, value: Path) -> str:
        """Translate path to string."""
        return value.as_posix()
