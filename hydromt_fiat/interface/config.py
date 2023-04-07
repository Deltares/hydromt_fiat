import os
from abc import ABC, abstractmethod
from typing import Union, Optional, List
from enum import Enum
from pydantic import BaseModel


class Mode(str, Enum):
    """Class describing the accepted input for the variable mode in the configuration file"""

    event = "event"
    risk = "risk"


class SpatialReference(str, Enum):
    """Class describing the accepted input for the variable spatial_reference in the configuration file"""

    dem = "dem"
    datum = "datum"


class OutputModel(BaseModel):
    output_dir: str
    crs: str


class HazardModel(BaseModel):
    grid_file: Union[str, os.PathLike]
    crs: str
    mode: Mode
    return_periods: Optional[List[int]]
    spatial_reference: SpatialReference


class ExposureModel(BaseModel):
    dbase_file: Union[str, os.PathLike]
    crs: str


class VulnerabilityModel(BaseModel):
    dbase_file: Union[str, os.PathLike]


class ConfigModel(BaseModel):
    """BaseModel describing the expected variables and data types of Delft-FIAT configuration attributes."""

    output: OutputModel
    hazard: HazardModel
    exposure: ExposureModel
    vulnerability: VulnerabilityModel


class IConfig(ABC):
    attrs: ConfigModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Get Delft-FIAT config attributes from a Delft-FIAT settings toml file."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Delft-FIAT config attributes to a Delft-FIAT settings toml file."""
