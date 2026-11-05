"""Settings for the exposure (file(s))."""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from hydromt_fiat.settings.base import BaseModelF
from hydromt_fiat.settings.file import InputFileModel
from hydromt_fiat.settings.variables import Variable
from hydromt_fiat.utils import IMPACT__TYPE

__all__ = ["ExposureGeometry", "ExposureGrid", "ExposureGridVariable"]


class ExposureGeometrySettings(BaseModel):
    """Settings for reading the exposure geometry data."""

    model_config = ConfigDict(extra="forbid")

    crs: str | None = Field(
        default=None,
        description="Spatial reference system of the file.",
    )


class ExposureGeometryVariable(BaseModelF):
    """Exposure geometry file variables."""

    area_method: str = Field(
        default="centroid",
        description="The method of extracting hazard values \
based on the exposure geometry.",
    )

    impact_type: list[str] = Field(
        default=["damage"],
        description="The impact types to be run for this exposure data.",
    )

    vulnerability: str = Field(
        default=...,
        description="The vulnerability dataset (variable) to use from the \
vulnerability netcdf dataset.",
    )

    zonal_method: str = Field(
        default="mean",
        description="The zonal statistics method. Only really applicable \
if `area_method` is set to 'area'.",
    )

    # Validator(s)
    @field_validator(IMPACT__TYPE, mode="before")
    @classmethod
    def ensure_impact_type_list(cls, value: str | list[str]):
        """Ensure impact type list typing."""
        if not isinstance(value, list):
            value = [value]
        return value


class ExposureGeometry(InputFileModel):
    """Exposure geometry settings for the FIAT model."""

    settings: ExposureGeometrySettings | None = Field(
        default=None,
        description="Settings for reading the exposure geometry data.",
    )

    variables: ExposureGeometryVariable = Field(
        default=...,
        description="Settings per exposure file.",
    )


class ExposureGridSettings(BaseModel):
    """Settings for reading the exposure grid data."""

    model_config = ConfigDict(extra="forbid")

    crs: str | None = Field(
        default=None,
        description="Spatial reference system of the file.",
    )


class ExposureGridVariable(Variable):
    """Settings for a variable (layer) of the exposure grid dataset."""

    fn_curve: str | int | None = Field(
        default=None,
        description="The curve id looked up in the linked vulnerability dataset(s).",
    )

    type: str = Field(
        default=...,
        description="The exposure type: 'default' or 'categorized' for a layer, \
'values' for a category-value variable.",
    )

    value: float | None = Field(
        default=None,
        description="Constant value of a uniform layer that is not in the file.",
    )

    values: list[str] | None = Field(
        default=None,
        description="The category-value variables of a categorized layer.",
    )

    vulnerability: str | list[str] | None = Field(
        default=None,
        description="The vulnerability dataset(s) linked to this variable.",
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

    variables: list[ExposureGridVariable] = Field(
        default=...,
        min_length=1,
        description="Settings per exposure variable (layer).",
    )
