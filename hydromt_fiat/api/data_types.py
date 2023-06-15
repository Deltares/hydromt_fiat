from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict, Union

from pydantic import BaseModel


class ExtractionMethod(str, Enum):
    centroid = "centroid"
    area = "area"


class Units(str, Enum):
    m = "meter"
    feet = "feet"


class Category(Enum):
    exposure = "exposure"
    hazard = "hazard"
    vulnerability = "vulnerability"


class Driver(Enum):
    vector = "vector"
    raster = "raster"
    xlsx = "xlsx"


class DataType(Enum):
    RasterDataset = "RasterDataset"
    GeoDataFrame = "GeoDataFrame"
    GeoDataset = "GeoDataset"
    DataFrame = "DataFrame"


class Meta(TypedDict):
    category: Category


class DataCatalogEntry(BaseModel):
    path: Union[str, Path]
    data_type: DataType
    driver: Driver
    crs: Optional[Union[str, int]]
    translation_fn: Optional[str]
    meta: Meta


class ModelIni(BaseModel):
    site_name: str
    scenario_name: str
    output_dir: Union[Path, str]
    crs: str


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


class ConfigIni(BaseModel):
    setup_config: ModelIni
    setup_hazard: HazardIni
    setup_vulnerability: VulnerabilityIni
    setup_exposure_vector: ExposureVectorIni
