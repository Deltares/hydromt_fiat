from enum import Enum
from typing_extensions import Optional, TypedDict, Union, List

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


class VulnerabilityIni(BaseModel):
    vulnerability_fn: str
    vulnerability_identifiers_and_linking_fn: str
    unit: Units
    functions_mean: Union[str, list]
    functions_max: Union[str, list, None]
    step_size: Union[float, None]


class ExposureBuildingsIni(BaseModel):
    asset_locations: str
    occupancy_type: str
    max_potential_damage: str
    ground_floor_height: str
    unit: Units
    extraction_method: ExtractionMethod
    damage_types : Union[List[str], None]


class ConfigIni(BaseModel):
    setup_config: ModelIni
    setup_vulnerability: VulnerabilityIni
    setup_exposure_buildings: ExposureBuildingsIni
