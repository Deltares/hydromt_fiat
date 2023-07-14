from typing import Dict, Optional, Union

from hydromt import DataCatalog

from hydromt_fiat.workflows.exposure_vector import ExposureVector
from hydromt_fiat.api.utils import make_catalog_entry
from hydromt_fiat.interface.database import IDatabase
import logging

from .data_types import (
    Category,
    DataCatalogEntry,
    DataType,
    Driver,
    ExposureVectorIni,
    ExtractionMethod,
    Units,
)


class ExposureViewModel:
    def __init__(
        self, database: IDatabase, data_catalog: DataCatalog, logger: logging.Logger
    ):
        self.exposure_model = ExposureVectorIni(
            asset_locations="",
            occupancy_type="",
            max_potential_damage=-999,
            ground_floor_height=-999,
            ground_floor_height_unit=Units.m.value,
            extraction_method=ExtractionMethod.centroid.value,
        )
        self.database: IDatabase = database
        self.data_catalog: DataCatalog = data_catalog
        self.logger: logging.Logger = logger

    def create_interest_area(self, **kwargs: str):
        fpath = kwargs.get("fpath")
        # self.database.write(fpath)  # Why is this done?

        catalog_entry = make_catalog_entry(
            name="area_of_interest",
            path=fpath,
            data_type=DataType.GeoDataFrame,
            driver=Driver.vector,
            crs=4326,
            meta={"category": Category.exposure},
        )

        self.data_catalog.from_dict(catalog_entry)  # type: ignore

    def set_asset_locations_source(
        self,
        input_source: str,
        fiat_key_maps: Optional[Dict[str, str]] = None,
        crs: Union[str, int] = None,
    ):
        if input_source == "NSI":
            # NSI is already defined in the data catalog
            # Add NSI to the configuration file
            self.exposure_model.asset_locations = input_source
            self.exposure_model.occupancy_type = input_source
            self.exposure_model.max_potential_damage = input_source
            self.exposure_model.ground_floor_height = 1  # TODO: make flexible
            self.exposure_model.ground_floor_height_unit = (
                Units.ft.value
            )  # TODO: make flexible

            # Download NSI from the database
            region = self.data_catalog.get_geodataframe("area_of_interest")
            exposure = ExposureVector(
                data_catalog=self.data_catalog,
                logger=self.logger,
                region=region,
                crs=crs,
            )

            exposure.setup_from_single_source(
                input_source,
                self.exposure_model.ground_floor_height,
                "centroid",  # TODO: MAKE FLEXIBLE
            )
            primary_object_types = (
                exposure.exposure_db["Primary Object Type"].unique().tolist()
            )
            secondary_object_types = (
                exposure.exposure_db["Secondary Object Type"].unique().tolist()
            )
            exposure.set_exposure_geoms_from_xy()

            return (
                exposure.exposure_geoms[0],
                primary_object_types,
                secondary_object_types,
            )

        elif input_source == "file" and fiat_key_maps is not None:
            # maybe save fiat_key_maps file in database
            # make calls to backend to derive file meta info such as crs, data type and driver
            crs: str = "4326"
            # save keymaps to database

            catalog_entry = DataCatalogEntry(
                path=input_source,
                data_type="GeoDataFrame",
                driver="vector",
                crs=crs,
                translation_fn="",  # the path to the fiat_key_maps file
                meta={"category": Category.exposure},
            )
            # make backend calls to create translation file with fiat_key_maps
            print(catalog_entry)
        # write to data catalog

    def create_extraction_map(self, *args):
        # TODO: implement callback
        # if no exceptions, then self.exposure_model.extraction_method = args[0]
        # else if
        # make backend call to api with arguments to set extraction method per object:
        # create first with default method. Then get uploaded or drawn area and merge with default methid
        # save file to database
        # change self.exposure_model.extraction_method to file
        ...
        # change self.exposure_model.extraction_method to file
