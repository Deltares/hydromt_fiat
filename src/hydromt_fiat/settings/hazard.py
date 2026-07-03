"""Settings for the hazard (file)."""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from hydromt_fiat.settings.file import InputFileModel


class HazardSettings(BaseModel):
    """Settings for reading the hazard data."""

    model_config = ConfigDict(extra="forbid")

    crs: str | None = Field(
        default=None,
        description="Spatial reference system of the file.",
    )


class Hazard(InputFileModel):
    """Hazard settings for the FIAT model."""

    rp: list[float] | None = Field(
        default=None,
        description="Return periods for the hazard values.",
    )
    settings: HazardSettings | None = Field(
        default=None,
        description="Settings for reading the hazard data.",
    )
