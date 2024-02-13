from typing import Dict, Optional, Union, List

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
    ExposureBuildingsSettings,
    ExposureSetupGroundFloorHeight,
    ExposureSetupDamages,
    ExposureSetupGroundElevation,
    ExposureRoadsSettings,
    ExtractionMethod,
    AggregationAreaSettings,
    Units,
)


class ExposureViewModel:
    def __init__(
        self, database: IDatabase, data_catalog: DataCatalog, logger: logging.Logger
    ):
        self.exposure_buildings_model = None
        self.exposure_roads_model = None
        self.aggregation_areas_model = None
        self.exposure_ground_floor_height_model = None
        self.exposure_damages_model = None
        self.exposure_ground_elevation_model = None
        self.exposure_occupancy_type_model = None

        self.database: IDatabase = database
        self.data_catalog: DataCatalog = data_catalog
        self.logger: logging.Logger = logger
        self.exposure: ExposureVector = None

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

    def set_asset_locations_source_and_get_data(
        self,
        source: str,
        ground_floor_height: str,
        fiat_key_maps: Optional[Dict[str, str]] = None,
        crs: Union[str, int] = None,
    ):
        if source == "NSI":
            # NSI is already defined in the data catalog
            self.set_asset_locations_source(source, ground_floor_height)

            # Download NSI from the database
            region = self.data_catalog.get_geodataframe("area_of_interest")
            self.exposure = ExposureVector(
                data_catalog=self.data_catalog,
                logger=self.logger,
                region=region,
                crs=crs,
            )

            self.exposure.setup_buildings_from_single_source(
                source,
                ground_floor_height,
                "centroid",
            )
            primary_object_types = (
                self.exposure.exposure_db["Primary Object Type"].unique().tolist()
            )
            secondary_object_types = (
                self.exposure.exposure_db["Secondary Object Type"].unique().tolist()
            )
            gdf = self.exposure.get_full_gdf(self.exposure.exposure_db)

            return (
                gdf,
                primary_object_types,
                secondary_object_types,
            )
            
    def set_asset_locations_source(
        self,
        source: str,
        ground_floor_height: str,
        fiat_key_maps: Optional[Dict[str, str]] = None,
        crs: Union[str, int] = None,
    ) -> None:
        if source == "NSI":
            # NSI is already defined in the data catalog
            self.exposure_buildings_model = ExposureBuildingsSettings(
                asset_locations=source,
                occupancy_type=source,
                max_potential_damage=source,
                ground_floor_height=ground_floor_height,
                unit=Units.ft.value,  # TODO: make flexible
                extraction_method=ExtractionMethod.centroid.value,
                damage_types=["structure", "content"],
            )
        elif source == "file" and fiat_key_maps is not None:
            # maybe save fiat_key_maps file in database
            # make calls to backend to derive file meta info such as crs, data type and driver
            crs: str = "4326"
            # save keymaps to database

            catalog_entry = DataCatalogEntry(
                path=source,
                data_type="GeoDataFrame",
                driver="vector",
                crs=crs,
                translation_fn="",  # the path to the fiat_key_maps file
                meta={"category": Category.exposure},
            )
            # make backend calls to create translation file with fiat_key_maps
            print(catalog_entry)
        # write to data catalog

    def update_occupancy_types(self, source, attribute, type_add):
        if self.exposure:
            self.exposure.setup_occupancy_type(source, attribute, type_add)

    def get_object_types(self):
        if self.exposure:
            primary_object_types = []
            secondary_object_types = []

            if "Primary Object Type" in self.exposure.exposure_db.columns:
                primary_object_types = (
                    self.exposure.exposure_db["Primary Object Type"].unique().tolist()
                )
            
            if "Secondary Object Type" in self.exposure.exposure_db.columns:
                secondary_object_types = (
                    self.exposure.exposure_db["Secondary Object Type"].unique().tolist()
                )
    
            return (
                primary_object_types,
                secondary_object_types,
            )

    def set_asset_data_source(self, source):
        self.exposure_buildings_model.asset_locations = source

    def setup_extraction_method(self, extraction_method):
        if self.exposure:
            self.exposure.setup_extraction_method(extraction_method)

    def set_ground_floor_height(
        self,
        source: str,
        attribute_name: Union[str, List[str], None] = None,
        gfh_method: Union[str, List[str], None] = "nearest",
        max_dist: Union[float, int, None] = 10,
    ):
        self.exposure_ground_floor_height_model = ExposureSetupGroundFloorHeight(
            source=source,
            attribute_name=attribute_name,
            gfh_method=gfh_method,
            max_dist=max_dist,
        )

    def set_damages(
        self,
        source: str,
        attribute_name: Union[str, List[str], None] = None,
        damage_types: Union[str, List[str], None] = None,
        method_damages: Union[str, List[str], None] = "nearest",
        max_dist: Union[float, int, None, List[float], List[int]] = 10,
    ):
        self.exposure_damages_model = ExposureSetupDamages(
            source=source,
            attribute_name=attribute_name,
            method_damages=method_damages,
            max_dist=max_dist,
            damage_types = damage_types,
        )

    def set_ground_elevation(self, source: Union[int, float, None, str]):
        self.exposure_ground_elevation_model = ExposureSetupGroundElevation(
            source=source
        )
    
    def set_roads_settings(
        self,
        road_types: List[str] = [
            "motorway",
            "motorway_link",
            "trunk",
            "trunk_link",
            "primary",
            "primary_link",
            "secondary",
            "secondary_link",
        ],
    ):
        self.exposure_roads_model = ExposureRoadsSettings(
            roads_fn="OSM",
            road_types=road_types,
            road_damage=1,
            vertical_unit=Units.ft.value,
        )

            
    def get_osm_roads(
        self,
        road_types: List[str] = [
            "motorway",
            "motorway_link",
            "trunk",
            "trunk_link",
            "primary",
            "primary_link",
            "secondary",
            "secondary_link",
        ],
        crs=4326,
    ):
        if self.exposure is None:
            region = self.data_catalog.get_geodataframe("area_of_interest")
            self.exposure = ExposureVector(
                data_catalog=self.data_catalog,
                logger=self.logger,
                region=region,
                crs=crs,
            )

        self.exposure.setup_roads(
            source="OSM",
            road_damage=1,
            road_types=road_types,
        )
        roads = self.exposure.exposure_db.loc[
            self.exposure.exposure_db["Primary Object Type"] == "roads"
        ]
        gdf = self.exposure.get_full_gdf(roads)

        self.exposure_roads_model = ExposureRoadsSettings(
            roads_fn="OSM",
            road_types=road_types,
            road_damage=1,
            vertical_unit=Units.ft.value,
        )

        return gdf

    def set_aggregation_areas_config(self, files, attribute_names, label_names):
        self.aggregation_areas_model = AggregationAreaSettings(
            aggregation_area_fn=files,
            attribute_names=attribute_names,
            label_names=label_names,
        )
