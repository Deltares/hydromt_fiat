"""Settings for the FIAT model."""

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationInfo,
    field_serializer,
    field_validator,
)

from hydromt_fiat.readers import read_config
from hydromt_fiat.utils import EXPOSURE, FLOOD_DEPTH, HAZARD, OUTPUT

from .exposure import ExposureGeometry, ExposureGrid
from .file import DEFAULT_CONTEXT, FileContext, InputFileModel, OutputFileModel
from .hazard import Hazard
from .utils import _relpath

__all__ = ["GeomSettings", "GridSettings"]


def get_file_from_settings_component(
    component: InputFileModel,
) -> Path | None:
    """Return file path if component exists."""
    if component is not None:
        return component.file
    return None


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


class BaseSettings(BaseModel):
    """Configuration for the Fiat model."""

    # Model wide settings
    loglevel: str = Field(default="INFO", description="The logging level of FIAT.")

    method: str = Field(
        default=FLOOD_DEPTH,
        description="Method to use for the model. \
Can be either 'flood.depth' or 'flood.level'.",
    )

    output_dir: Path = Field(
        default=Path("output"),
        description="Directory to store the output of the model.",
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

    # Model projection
    projection: ModelProjection = Field(
        default=ModelProjection(), description="The model wide projection."
    )

    # Input files
    vulnerability: InputFileModel | None = Field(
        default=None,
        description="Vulnerability settings for the model.",
    )

    hazard: Hazard | None = Field(
        default=None,
        description="Hazard settings for the model.",
    )

    # Serializer(s)
    @field_serializer("output_dir")
    def serialize_path(self, value: Path, info: ValidationInfo) -> str:
        """Translate output directory to string."""
        context: FileContext = info.context or DEFAULT_CONTEXT
        return _relpath(value=value, root=context.config_dir)

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


DEFAULT_SETTINGS = BaseSettings()


class GeomSettings(BaseSettings):
    """Geometry model settings."""

    type: Literal["geom"] = "geom"

    geom: ModelGeom | None = Field(
        default=None,
        description="The model settings specific to the geometry model.",
    )

    output: list[OutputFileModel] | None = Field(
        default=None,
        description="The output file settings for the geometry model.",
    )

    exposure: list[ExposureGeometry] | None = Field(
        default=None,
        description="Exposure geometry settings for the FIAT model.",
    )

    # Validator(s)
    @field_validator(EXPOSURE, mode="before")
    @classmethod
    def ensure_exposure_list(cls, value):
        """Ensure exposure list typing."""
        if not isinstance(value, list) and value is not None:
            value = [value]
        return value

    @field_validator(OUTPUT, mode="before")
    @classmethod
    def ensure_output_list(cls, value):
        """Ensure output list typing."""
        if not isinstance(value, list) and value is not None:
            value = [value]
        return value


DEFAULT_GEOM_SETTINGS = GeomSettings()


class GridSettings(BaseSettings):
    """Geometry model settings."""

    type: Literal["grid"] = "grid"

    grid: ModelGrid | None = Field(
        default=None,
        description="The model settings specific to the grid model.",
    )

    output: OutputFileModel | None = Field(
        default=None,
        description="The output file settings for the grid model.",
    )

    exposure: ExposureGrid | None = Field(
        default=None,
        description="Exposure grid settings for the FIAT model.",
    )


DEFAULT_GRID_SETTINGS = GridSettings()

Settings = Annotated[
    GeomSettings | GridSettings,
    Field(discriminator="type"),
]


def load_settings(filename: Path | str) -> GeomSettings | GridSettings:
    """Read and load the settings toml into a validated structure.

    This is a standalone function similar to the `from_toml` methods of the
    BaseSettings class.
    """
    settings_dict = read_config(filename)

    # Let the adapter sort out which settings class it should be
    settings: BaseSettings = TypeAdapter(Settings).validate_python(
        settings_dict,
        context=FileContext(config_dir=filename.parent),
    )

    # Return the settings
    return settings
