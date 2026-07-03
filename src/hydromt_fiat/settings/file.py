"""Base model for (input) files."""

from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
)

from hydromt_fiat.settings.utils import _relpath


class FileContext(BaseModel):
    """Context for in- and output files."""

    config_dir: Path | None = Field(
        default=None,
        description="Path of the config file directory.",
    )

    output_dir: Path | None = Field(
        default=None,
        description="Path of the directory of the model output.",
    )


DEFAULT_CONTEXT = FileContext()


class InputFileModel(BaseModel):
    """Input file base model."""

    file: Path = Field(
        default=...,
        description="Path to the input file.",
    )

    @field_validator("file", mode="before")
    @classmethod
    def validate_file(cls, value: Path | str, info: ValidationInfo):
        """Make the path absolute with the config file directory."""
        context: FileContext = info.context or DEFAULT_CONTEXT
        path = Path(value)
        if path.is_absolute():
            return path
        if context.config_dir is not None:
            return Path(context.config_dir, path)

        return path

    @field_serializer("file")
    def serialize_file(self, value: Path, info: SerializationInfo) -> str:
        """Make the paths relative to the config file."""
        context: FileContext = info.context or DEFAULT_CONTEXT
        if context.config_dir is not None:
            return _relpath(value=value, root=context.config_dir)

        return value.as_posix()


class OutputFileModel(BaseModel):
    """Output file base model."""

    file: Path = Field(
        default=...,
        description="Path to the output file.",
    )

    @field_validator("file", mode="before")
    @classmethod
    def validate_file(cls, value: Path | str, info: ValidationInfo):
        """Make the path absolute with the config file directory."""
        context: FileContext = info.context or DEFAULT_CONTEXT
        path = Path(value)
        if path.is_absolute():
            return path
        if context.output_dir is not None:
            return Path(context.output_dir, path)

        return path

    @field_serializer("file")
    def serialize_file(self, value: Path, info: SerializationInfo) -> str:
        """Make the paths relative to the config file."""
        context: FileContext = info.context or DEFAULT_CONTEXT
        if context.output_dir is not None:
            return _relpath(value=value, root=context.output_dir)

        return value.as_posix()
