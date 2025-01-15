from enum import Enum
from typing_extensions import Optional, TypedDict, Union, List

from pydantic import BaseModel, Extra


class ExtractionMethod(str, Enum):
    centroid = "centroid"
    area = "area"


class Units(str, Enum):
    meters = "meters"
    feet = "feet"

class Conversion(float, Enum):
    meters_to_feet = 3.28084
    feet_to_meters = 0.3048
    eur_to_us_dollars = 1.327 #Average exchange rate in 2010


class Currency(str, Enum):
    dollar = "$"
    euro = "€"


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
    crs: Optional[Union[str, int]] = None
    translation_fn: Optional[str] = None
    meta: Meta


class GlobalSettings(BaseModel):
    crs: Union[str, int]


class OutputSettings(BaseModel):
    output_dir: str
    output_csv_name: str
    output_vector_name: str


class VulnerabilitySettings(BaseModel):
    vulnerability_fn: str
    vulnerability_identifiers_and_linking_fn: str
    unit: Units
    functions_mean: Union[str, list]
    functions_max: Optional[Union[str, list]] = None
    step_size: Optional[float] = None  # TODO should this have a default value?
    continent: Optional[str] = None


class ExposureBuildingsSettings(BaseModel):
    asset_locations: str
    occupancy_type: str
    max_potential_damage: str
    ground_floor_height: Union[str, float]
    gfh_unit: Units = None
    unit: Units
    extraction_method: ExtractionMethod
    damage_types: Optional[List[str]] = None
    damage_unit: str
    country: str = None
    bf_conversion: bool = False
    keep_unclassified: bool = True
    grnd_elev_unit: Units = None


class ExposureSetupGroundFloorHeight(BaseModel):
    source: str
    gfh_attribute_name: Optional[Union[str, List[str]]] = None
    gfh_method: Optional[Union[str, List[str]]] = None
    max_dist: Optional[Union[float, int]] = None
    gfh_unit: Units = None


class ExposureSetupGroundElevation(BaseModel):
    source: Union[int, float, None, str]
    grnd_elev_unit: Units = None


class ExposureSetupDamages(BaseModel):
    source: Union[str, List[str]]
    attribute_name: Optional[Union[str, List[str]]] = None
    method_damages: Optional[Union[str, List[str]]] = None
    max_dist: Optional[Union[float, int, List[float], List[int]]] = None
    damage_types: Optional[Union[str, List[str]]] = None


class RoadVulnerabilitySettings(BaseModel):
    threshold_value: Union[float, None]
    min_hazard_value: float
    max_hazard_value: float
    step_hazard_value: float
    vertical_unit: Units


class ExposureRoadsSettings(BaseModel):
    roads_fn: str
    road_types: Union[List[str], bool]
    road_damage: Union[int, float, None]
    unit: Units


class AggregationAreaSettings(BaseModel):
    aggregation_area_fn: Union[List[str], str]
    attribute_names: Union[List[str], str]
    label_names: Union[List[str], str]
    new_composite_area: bool


class ClassificationSettings(BaseModel):
    source: Union[List[str], str]
    attribute: Union[List[str], str]
    type_add: Union[List[str], str]
    old_values: Union[List[str], str]
    new_values: Union[List[str], str]
    damage_types: Union[List[str], str]
    remove_object_type: bool


class SocialVulnerabilityIndexSettings(BaseModel):
    census_key: str
    codebook_fn: str
    year_data: int


class EquityDataSettings(BaseModel):
    census_key: str
    year_data: int


class ConfigYaml(BaseModel, extra=Extra.allow):
    setup_global_settings: GlobalSettings
    setup_output: OutputSettings
