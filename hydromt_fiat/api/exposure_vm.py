from typing import Dict, Optional, Union, List

from hydromt import DataCatalog

from hydromt_fiat.workflows.exposure_vector import ExposureVector
from hydromt_fiat.api.utils import make_catalog_entry
from hydromt_fiat.interface.database import IDatabase
from hydromt_fiat.api.data_types import Currency
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
    ClassificationSettings,
    Units,
)


class ExposureViewModel:
    def __init__(
        self, database: IDatabase, data_catalog: DataCatalog, logger: logging.Logger
    ):
        self.exposure_buildings_model = None
        self.exposure_roads_model = None
        self.aggregation_areas_model = None
        self.classification_model = None
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
        country: str = None,
        max_potential_damage: str = None,
        fiat_key_maps: Optional[Dict[str, str]] = None,
        crs: Union[str, int] = None,
        grnd_elev_unit: Units = None,
        bf_conversion: bool = False,
        keep_unclassified: bool = True,
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
                unit=Units.feet.value,
            )
        
            self.exposure.setup_buildings_from_single_source(
                source,
                ground_floor_height,
                "centroid",
            )
            primary_object_types = (
                self.exposure.exposure_db["primary_object_type"].unique().tolist()
            )
            secondary_object_types = (
                self.exposure.exposure_db["secondary_object_type"].unique().tolist()
            )
            gdf = self.exposure.get_full_gdf(self.exposure.exposure_db)

            return (
                gdf,
                primary_object_types,
                secondary_object_types,
            )
        elif source == "OSM":
            self.set_asset_locations_source(
                source,
                ground_floor_height,
                max_potential_damage,
                country=country,
                bf_conversion=bf_conversion,
                keep_unclassified=keep_unclassified,
            )

            # Download OSM from the database
            region = self.data_catalog.get_geodataframe("area_of_interest")

            self.exposure = ExposureVector(
                data_catalog=self.data_catalog,
                logger=self.logger,
                region=region,
                crs=crs,
                unit=Units.meters.value,
                )
            
            self.exposure.setup_buildings_from_multiple_sources(
                asset_locations=source,
                occupancy_source=source,
                max_potential_damage="jrc_damage_values",
                ground_floor_height=ground_floor_height,
                extraction_method="centroid",
                damage_types=["structure", "content"],
                country=country,
                grnd_elev_unit=grnd_elev_unit,
                bf_conversion=bf_conversion,
                keep_unclassified=keep_unclassified,
            )
            primary_object_types = (
                self.exposure.exposure_db["primary_object_type"].unique().tolist()
            )
            secondary_object_types = (
                self.exposure.exposure_db["secondary_object_type"].unique().tolist()
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
        max_potential_damage: str = None,
        fiat_key_maps: Optional[Dict[str, str]] = None,
        crs: Union[str, int] = None,
        country: str = None,
        bf_conversion: bool = False,
        keep_unclassified: bool = True,
    ) -> None:
        if source == "NSI":
            # NSI is already defined in the data catalog
            self.exposure_buildings_model = ExposureBuildingsSettings(
                asset_locations=source,
                occupancy_type=source,
                max_potential_damage=source,
                ground_floor_height=ground_floor_height,
                unit=Units.feet.value, 
                extraction_method=ExtractionMethod.centroid.value,
                damage_types=["structure", "content"],
                damage_unit=Currency.dollar.value,
                country="United States",
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
        elif source == "OSM":
            # download OSM data
            self.exposure_buildings_model = ExposureBuildingsSettings(
                asset_locations=source,
                occupancy_type=source,
                keep_unclassified=keep_unclassified,
                max_potential_damage=max_potential_damage,
                ground_floor_height=ground_floor_height,
                unit=Units.meters.value,
                extraction_method=ExtractionMethod.centroid.value,
                damage_types=["structure", "content"],
                damage_unit=Currency.euro.value,
                country=country,
                bf_conversion=bf_conversion,
            )

    def update_occupancy_types(
        self, source, attribute, type_add, keep_unclassified=True
    ):
        if self.exposure:
            self.exposure.setup_occupancy_type(
                source, attribute, type_add, keep_unclassified
            )

    def get_object_types(self):
        if self.exposure:
            primary_object_types = []
            secondary_object_types = []

            if "primary_object_type" in self.exposure.exposure_db.columns:
                primary_object_types = (
                    self.exposure.exposure_db["primary_object_type"].unique().tolist()
                )

            if "secondary_object_type" in self.exposure.exposure_db.columns:
                secondary_object_types = (
                    self.exposure.exposure_db["secondary_object_type"].unique().tolist()
                )

            return (
                primary_object_types,
                secondary_object_types,
            )

    def set_asset_data_source(self, source):
        self.exposure_buildings_model.asset_locations = source

    def set_country(self, country):
        self.exposure_buildings_model.country = country

    def setup_extraction_method(self, extraction_method):
        if self.exposure:
            self.exposure.setup_extraction_method(extraction_method)

    def set_ground_floor_height(
        self,
        source: str,
        gfh_attribute_name: Union[str, List[str], None] = None,
        gfh_method: Union[str, List[str], None] = "nearest",
        max_dist: Union[float, int, None] = 10,
    ):
        self.exposure_ground_floor_height_model = ExposureSetupGroundFloorHeight(
            source=source,
            gfh_attribute_name=gfh_attribute_name,
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
            damage_types=damage_types,
        )

    def set_ground_elevation(
        self,
        source: Union[
            int,
            float,
            None,
            str,
        ],
        grnd_elev_unit: Units,
    ):
        self.exposure_ground_elevation_model = ExposureSetupGroundElevation(
            source=source, grnd_elev_unit=grnd_elev_unit
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
            road_damage=None,
            unit=Units.feet.value,
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
            road_damage=None,
            road_types=road_types,
        )
        roads = self.exposure.exposure_db.loc[
            self.exposure.exposure_db["primary_object_type"] == "roads"
        ]
        gdf = self.exposure.get_full_gdf(roads)

        self.exposure_roads_model = ExposureRoadsSettings(
            roads_fn="OSM",
            road_types=road_types,
            road_damage=None,
            unit=Units.feet.value,
        )

        return gdf

    def set_aggregation_areas_config(
        self, files, attribute_names, label_names, new_composite_area=False
    ):
        self.aggregation_areas_model = AggregationAreaSettings(
            aggregation_area_fn=files,
            attribute_names=attribute_names,
            label_names=label_names,
            new_composite_area=new_composite_area,
        )

    def set_classification_config(
        self,
        source,
        attribute,
        type_add,
        old_values,
        new_values,
        damage_types,
        remove_object_type,
    ):
        self.classification_model = ClassificationSettings(
            source=source,
            attribute=attribute,
            type_add=type_add,
            old_values=old_values,
            new_values=new_values,
            damage_types=damage_types,
            remove_object_type=remove_object_type,
        )

        """_summary_

        Parameters
        ----------
        source : Union[List[str], List[Path], str, Path]
            Path(s) to the user classification file.
        attribute : Union[List[str], str]
            Name of the column of the user data
       type_add : Union[List[str], str]
            Name of the attribute the user wants to update. Primary or Secondary
        old_values : Union[List[str], List[Path], str, Path]
            Name of the default (NSI) exposure classification
        new_values : Union[List[str], str]
            Name of the user exposure classification.
        exposure_linking_table : Union[List[str], str]
            Path(s) to the new exposure linking table(s).
        damage_types : Union[List[str], str]
            "structure"or/and "content"
        remove_object_type: bool
            True if Primary/secondary_object_type from old gdf should be removed in case the object type category changed completely eg. from RES to COM.
            E.g. primary_object_type holds old data (RES) and Secondary was updated with new data (COM2).
        """
