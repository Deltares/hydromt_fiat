from typing import Dict, Optional, cast

import geopandas as gpd

from .data_types import (
    Category,
    DataCatalogEntry,
    ExposureVectorIni,
    ExtractionMethod,
    Units,
)


class ExposureViewModel:
    def __init__(
        self,
    ):
        self.exposure_model = ExposureVectorIni(
            asset_locations=" ",
            occupancy_type="",
            max_potential_damage=-999,
            ground_floor_height=-999,
            gfh_units=Units.feet,
            extraction_method=ExtractionMethod.centroid,
        )

    def create_interest_area(self, **kwargs: str):
        filepath = kwargs.get("filepath")

        entry = DataCatalogEntry(
            path=filepath,
            data_type="GeoDataFrame",
            driver="vector",
            crs=4326,
            meta={"category": Category.exposure},
        )  # type: ignore
        print(entry)

        # create entry in datacatalog in database
        ...

    def create_location_source(
        self, input_source: str, fiat_key_maps: Optional[Dict[str, str]] = None
    ):
        if input_source == "NSI":
            # NSI is already defined in the data catalog
            # Add NSI to the configuration file

            ...
        elif input_source == "file" and fiat_key_maps is not None:
            # maybe save fiat_key_maps file in database
            # make calls to backend to derive file meta info such as crs, data type and driver
            crs: str = cast(str, gpd.read_file(input_source).crs.to_epsg())

            # save keymaps to database

            entry = DataCatalogEntry(
                path=input_source,
                data_type="GeoDataFrame",
                driver="vector",
                crs=crs,
                translation_fn="",  # the path to the fiat_key_maps file
                meta={"category": Category.exposure},
            )
            # make backend calls to create translation file with fiat_key_maps
            print(entry)
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
        ...
        ...
