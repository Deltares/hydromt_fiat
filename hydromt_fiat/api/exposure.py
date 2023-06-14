from ast import Dict
from pathlib import Path
from typing import Union
from xml.dom.expatbuilder import ExpatBuilder

from pydantic import BaseModel

from .util_types import Category, DataCatalogEntry, ExtractionMethod, Units


class ExposureVectorIni(BaseModel):
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
        self.exposure_model = ExposureVectorIni(
            asset_locations="",
            occupancy_type="",
            max_potential_damage=-999,
            ground_floor_height=-999,
            gfh_units=Units.feet,
            extraction_method=ExtractionMethod.centroid,
        )

    def create_interest_area(self, **kwargs):
        filepath = kwargs.get("filepath")
        # make calls to backend to deduce data_type, driver, crs

        entry_data_catalog = DataCatalogEntry(
            path=filepath,
            data_type="",
            driver="",
            crs="",
            meta={"category": Category.exposure},
        )
        # create entry in datacatalog in database
        ...

    # def set_asset_location(self, **kwargs):
    #     location_source = kwargs("variable")
    #     # derive file meta info such as crs, data type and driver
    #     DataCatalogEntry(
    #         path=location_source,
    #         data_type="",
    #         driver="",
    #         crs="",
    #         meta={"category": Category.exposure},
    #     )
        
    #     # self.set_asset_loca
    #     ...

    def create_location_source(self, **kwargs):
        location_source: str = kwargs.get("variable", "NSI")
        fiat_key_maps: dict | None = kwargs.get("keys", None)
        
        if location_source == "NSI":
            # make calls to backend to derive file meta info such as crs, data type and driver
            # make backend calls to create translation file
            
  
            ...
        elif (location_source == "file" and fiat_key_maps is not None):
            # maybe save fiat_key_maps file in database
            # make calls to backend to derive file meta info such as crs, data type and driver
            # make backend calls to create translation file with fiat_key_maps
            ...
            
        # save translation file in data base
        # create data catalog entry
        new_entry = DataCatalogEntry(
            path=location_source,
            data_type="",
            driver="",
            crs="",
            translation_fn=""
            meta={"category": Category.exposure},
        )

        # write to data catalog

    def create_extraction_map(self, *args):
        # if no exceptions, then self.exposure_model.extraction_method = args[0]
        # else if
        # make backend call to api with arguments to set extraction method per object:
        # create first with default method. Then get uploaded or drawn area and merge with default methid
        # save file to database
        # change self.exposure_model.extraction_method to file
        ...
        # change self.exposure_model.extraction_method to file
        ...
