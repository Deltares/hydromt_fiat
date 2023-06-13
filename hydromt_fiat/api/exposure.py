from enum import Enum
from pathlib import Path
from typing import Union

from pydantic import BaseModel


class ExtractionMethod(str, Enum):
    centroid = "centroid"
    area = "area"


class Units(Enum):
    m = "meter"
    feet = "feet"


class ExposureVector(BaseModel):
    asset_locations: Union[str, Path]
    occupancy_type: Union[str, Path]
    max_potential_damage: Union[int, Path]
    ground_floor_height: Union[int, Path]
    gfh_units: Units
    extraction_method: ExtractionMethod


class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance


class ExposureViewModel(Singleton):
    def __init__(self):
        self.interest_area: str
        self.exposure_model: ExposureVector

    def draw_area(self, *args):
        # set self.interest_area to file name generated with draw_area
        ...

    def upload(self, *args):
        # check if file exists
        if args == "file":
            # copy file over to database
            # create file in database and set self.interest_area

            ...

    def create_location_source(self, *args):
        if args == "file":
            # make calls to backend
            # create file in database and set attribute in model
            # change attribute in datacatalog
            # set attribute in exposure model to point to data catalog
            ...
        elif args == "NSI":
            # make calls to back end to generate automatically json file and save in data
            # base
            # change attribute in data catalog and set exposure model
            # attribute to point to data
            ...

    def create_extraction_map(self, *args):
        # if no exceptions, then self.exposure_model.extraction_method = args[0]
        # else if
        # make backend call to api with arguments to set extraction method per object:
        # create first with default method. Then get uploaded or drawn area and merge with default methid
        # save file to database
        # change self.exposure_model.extraction_method to file
        ...
