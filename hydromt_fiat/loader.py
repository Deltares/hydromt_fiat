from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

import tomli
import tomli_w
from pydantic import BaseModel

from hydromt_fiat.interface.database import IDatabase
class ExtractionMethod(str, Enum):
    centroid: ExtractionMethod = "centroid"
    area = "area"
class ExposureVector(BaseModel):
    asset_locations: Union[str, Path]
    occupancy_type: Union[str, Path]
    max_potential_damage: Union[int, Path]
    ground_floor_height: Union[int, Path]
    gfh_units: Units
    extraction_method: ExtractionMethod
    
class ExposureViewModel:
    def __init__(self, database: IDatabase):
        self.exposure_model: ExposureVector

    def set_interest_area(self, *args):
        if (args ==  "file"):
            # enforce to be file
            # create file in database and set attribute in model
            # change in data catalog
            ...

    def create_location_source(self, *args):
        if (args == "file"):
            # create file in database and set attribute in model
            # change attribute in datacatalog
            # set attribute in exposure model to point to data catalog
            # make calls to backend 
            ...
        elif (args == "NSI"):
            # make calls to back end to generate automatically json file and save in data
            # base
            # change attribute in data catalog and set exposure model
            # attribute to point to data
            ...
    def set_extraction_method(self, *args):
        self.exposure_model.extraction_method = "centroid"
        
    def set_extraction_map(self, *args):
        # make the associated back end call
        # save the new file in the database and update the data catalog
        # update the exposure_model pointer
        ...
    
    def upload_classification(self, *args):
        ...
        
    

            
        
    def serialize():
        ExtractionMethodViewModel.ExtractionMethodModel.serialize()
        ExtractionMethodViewModel.ExtractionMethodModel.serialize()
        ExtractionMethodViewModel.ExtractionMethodModel.serialize()
        

class ExposureModel:
    def __init__():
        self.hazard = Hazard()

class ExtractionMethodViewModel:
    __init__():
        self.ExtractionMethodModel = ExtractionMethod()
        
    def on_changed_dropdownbox(self, centroid):
       self.ExtractionMethodViewModel.set_centroid()
         
         
class ExtractionMethod(str, Enum):
    centroid: ExtractionMethod = "centroid"
    area = "area"


class Units(Enum):
    m = "meter"
    feet = "feet"


class Config(BaseModel):
    output_dir: Path
    crs: str


class Hazard(BaseModel):
    hazard_map_fn: Union[str, Path]
    hazard_type: str
    return_period: Optional[Union[int, None]] = None
    crs: Optional[str] = None
    no_data: Optional[int] = -9999
    var: Optional[Union[str, None]] = None
    chunks: Optional[Union[int, str]] = "auto"


class Vulnerability(BaseModel):
    vulnerability_fn: Union[str, Path]
    link_table: Union[str, Path]
    units: Units


class ExposureVector(BaseModel):
    asset_locations: Union[str, Path]
    occupancy_type: Union[str, Path]
    max_potential_damage: Union[int, Path]
    ground_floor_height: Union[int, Path]
    gfh_units: Units
    extraction_method: ExtractionMethod


class ExposureGrid(BaseModel):
    ...


class HydroMTConfig(BaseModel):
    setup_config: Config | None
    setup_hazard: Hazard | None
    setup_vulnerability: Vulnerability | None
    setup_exposure_vector: Optional[ExposureVector]


class ConfigHandler:
    def __init__(self):
        self.attrs: HydroMTConfig

    @staticmethod
    def load_file(filepath: Path | str) -> object:
        try:
            obj = ConfigHandler()
            with open(filepath, "rb") as f:
                toml_dict = tomli.load(f)
                obj.attrs = HydroMTConfig.parse_obj(toml_dict)
                return obj
        except FileNotFoundError as err:
            print(f"Error no {err.errno}: {err.strerror} {err.filename}")

    @staticmethod
    def load_dict(model_dict: Dict[str, Any]) -> object:
        try:
            obj = ConfigHandler()
            obj.attrs = HydroMTConfig.parse_obj(model_dict)

            return obj

        except Exception as err:
            print(f"{err}")

    def save(self, filepath: Path) -> None:
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(), f)
