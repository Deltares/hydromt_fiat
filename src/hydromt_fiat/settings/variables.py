"""Settings for the variables of the input datasets."""

from pydantic import (
    ConfigDict,
    Field,
)

from hydromt_fiat.settings.base import BaseModelF

__all__ = [
    "Variable",
]


class Variable(BaseModelF):
    """Base settings for a variable of an input dataset."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        default=...,
        description="Name of the variable in the dataset.",
    )
