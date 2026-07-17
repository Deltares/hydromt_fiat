"""Settings for the FIAT model."""

from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    model_serializer,
)

from .exposure import Exposure, ExposureGeometry, ExposureGrid
from .file import DEFAULT_CONTEXT, FileContext
from .hazard import Hazard
from .model import Model
from .output import Output
from .vulnerability import Vulnerability

__all__ = ["Settings"]


def get_file_from_settings_component(
    component: ExposureGeometry | ExposureGrid | Hazard | Vulnerability,
) -> Path | None:
    """Return file path if component exists."""
    if component is not None:
        return component.file
    return None


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

    # Serialzier
    @model_serializer(mode="wrap")
    def serialize(self, handler):
        """Serialize helper."""
        data = handler(self)
        if self.exposure.is_empty:
            data.pop("exposure", None)
        return data

    # Export
    def to_dict(
        self,
        context: FileContext = DEFAULT_CONTEXT,
    ) -> dict[str, Any]:
        """Export to settings to a dictionary.

        Parameters
        ----------
        context : FileContext, optional
            The file context for input and output files, by default DEFAULT_CONTEXT.

        Returns
        -------
        dict[str, Any]
            The settings as a dictionary.
        """
        data = self.model_dump(
            context=context,
            exclude_none=True,
        )
        return data


DEFAULT_SETTINGS = Settings()
