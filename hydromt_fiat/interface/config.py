import os
from abc import ABC, abstractmethod
from typing import Union, Optional, List
from enum import Enum
from pydantic import BaseModel


class SpatialReference(str, Enum):
    """Class describing the accepted input for the variable spatial_reference in the configuration file"""

    dem = "dem"
    datum = "datum"


class OutputCsv(BaseModel):
    name: str


class OutputGeom(BaseModel):
    name1: str


class OutputModel(BaseModel):
    path: str
    csv: OutputCsv
    geom: OutputGeom


class HazardModel(BaseModel):
    file: str
    crs: str
    risk: bool
    return_periods: Optional[List[int]] = None
    spatial_reference: SpatialReference
    layer: Optional[str] = None


class ExposureGeomModel(BaseModel):
    csv: str
    crs: str
    file1: str
    file2: str
    unit: str
    damage_unit: str


class ExposureModel(BaseModel):
    geom: ExposureGeomModel


class VulnerabilityModel(BaseModel):
    file: str
    step_size: float
    unit: str


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
        ...
