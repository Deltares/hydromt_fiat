from enum import Enum
from typing import Optional, TypedDict, Union

from pydantic import BaseModel


class ExtractionMethod(str, Enum):
    centroid = "centroid"
    area = "area"


class Units(str, Enum):
    m = "meter"
    ft = "feet"


class Category(str, Enum):
    exposure = "exposure"
    hazard = "hazard"
    vulnerability = "vulnerability"


class Driver(str, Enum):
    vector = "vector"
    raster = "raster"
    xlsx = "xlsx"


class DataType(str, Enum):
    RasterDataset = "RasterDataset"
    GeoDataFrame = "GeoDataFrame"
    GeoDataset = "GeoDataset"
    DataFrame = "DataFrame"


class Meta(TypedDict):
    category: Category


class DataCatalogEntry(BaseModel):
    path: str
    data_type: DataType
    driver: Driver
    crs: Optional[Union[str, int]]
    translation_fn: Optional[str]
    meta: Meta


class ModelIni(BaseModel):
    site_name: str
    scenario_name: str
    output_dir: str
    crs: str


class ExposureVectorIni(BaseModel):
    asset_locations: str
    occupancy_type: str
    max_potential_damage: str
    ground_floor_height: str
    ground_floor_height_unit: Units
    extraction_method: ExtractionMethod


class HazardIni(BaseModel):
    hazard_map_fn: str
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
    vulnerability_fn: str
    link_table: str
    units: Units


class ConfigIni(BaseModel):
    setup_config: ModelIni
    setup_hazard: HazardIni
    setup_vulnerability: VulnerabilityIni
    setup_exposure_vector: ExposureVectorIni
