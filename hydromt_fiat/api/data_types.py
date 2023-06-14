from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict, Union

from pydantic import BaseModel


class ExtractionMethod(str, Enum):
    centroid = "centroid"
    area = "area"


class Units(Enum):
    m = "meter"
    feet = "feet"


class Category(Enum):
    exposure = "exposure"
    hazard = "hazard"
    vulnerability = "vulnerability"


class Meta(TypedDict):
    category: Category


class DataCatalogEntry(BaseModel):
    path: Union[str, Path]
    data_type: str
    driver: str
    crs: Optional[str]
    translation_fn: Optional[str]
    meta: Meta


class ExposureVectorIni(BaseModel):
    asset_locations: Union[str, Path]
    occupancy_type: Union[str, Path]
    max_potential_damage: Union[int, Path]
    ground_floor_height: Union[int, Path]
    gfh_units: Units
    extraction_method: ExtractionMethod


class HazardIni(BaseModel):
    hazard_map_fn: Union[str, Path]
    hazard_type: str
    return_period: Optional[Union[int, None]] = None
    crs: Optional[str] = None
    no_data: Optional[int] = -9999
    var: Optional[Union[str, None]] = None
    chunks: Optional[Union[int, str]] = "auto"
    no_data: Optional[int] = -9999
    var: Optional[Union[str, None]] = None
    chunks: Optional[Union[int, str]] = "auto"


class VulnerabilityIni(BaseModel):
    vulnerability_fn: Union[str, Path]
    link_table: Union[str, Path]
    units: Units
