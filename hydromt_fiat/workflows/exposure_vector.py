import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from hydromt.data_catalog import DataCatalog
from pyproj import CRS

from hydromt_fiat.data_apis.national_structure_inventory import get_assets_from_nsi
from hydromt_fiat.data_apis.open_street_maps import (
    get_assets_from_osm,
    get_landuse_from_osm,
    get_roads_from_osm,
)

from hydromt_fiat.workflows.damage_values import (
    preprocess_jrc_damage_values,
    preprocess_hazus_damage_values,
)
from hydromt_fiat.workflows.exposure import Exposure
from hydromt_fiat.workflows.utils import detect_delimiter
from hydromt_fiat.workflows.vulnerability import Vulnerability
from hydromt_fiat.workflows.gis import (
    get_area,
    sjoin_largest_area,
    get_crs_str_from_gdf,
    join_spatial_data,
    ground_elevation_from_dem,
)

from hydromt_fiat.workflows.roads import (
    get_max_potential_damage_roads,
    get_road_lengths,
)

from hydromt_fiat.workflows.aggregation_areas import join_exposure_aggregation_areas


class ExposureVector(Exposure):
    _REQUIRED_COLUMNS = ["Object ID", "Extraction Method", "Ground Floor Height"]
    _REQUIRED_VARIABLE_COLUMNS = ["Damage Function: {}", "Max Potential Damage: {}"]
    _OPTIONAL_COLUMNS = [
        "Object Name",
        "Primary Object Type",
        "Secondary Object Type",
        "Ground Elevation",
    ]
    _OPTIONAL_VARIABLE_COLUMNS = ["Aggregation Label: {}", "Aggregation Variable: {}"]

    _CSV_COLUMN_DATATYPES = {
        "Object ID": int,
        "Object Name": str,
        "Primary Object Type": str,
        "Secondary Object Type": str,
        "Extraction Method": str,
        "Aggregation Label": str,
        "Damage Function: Structure": str,
        "Damage Function: Content": str,
        "Ground Flood Height": float,
        "Ground Elevation": float,
        "Max Potential Damage: Structure": float,
        "Max Potential Damage: Content": float,
    }

    def __init__(
        self,
        data_catalog: DataCatalog = None,
        logger: logging.Logger = None,
        region: gpd.GeoDataFrame = None,
        crs: str = None,
        unit: str = "m",
    ) -> None:
        """Transforms data into Vector Exposure data for Delft-FIAT.

        Parameters
        ----------
        data_catalog : DataCatalog, optional
            The HydroMT DataCatalog, by default None
        logger : logging.Logger, optional
            A logger object, by default None
        region : gpd.GeoDataFrame, optional
            The region of interest, by default None
        crs : str, optional
            The CRS of the Exposure data, by default None
        """
        super().__init__(
            data_catalog=data_catalog, logger=logger, region=region, crs=crs
        )
        self.exposure_db = pd.DataFrame()
        self.exposure_geoms = list()  # A list of GeoDataFrames
        self.unit = unit
        self._geom_names = list()  # A list of (original) names of the geometry (files)

    def bounding_box(self):
        if len(self.exposure_geoms) > 0:
            gdf = gpd.GeoDataFrame(pd.concat(self.exposure_geoms, ignore_index=True))
            return gdf.total_bounds

    def read_table(self, fn: Union[str, Path]):
        """Read the Delft-FIAT exposure data.

        Parameters
        ----------
        fn : Union[str, Path]
            Path to the exposure data.
        """
        csv_delimiter = detect_delimiter(fn)
        self.exposure_db = pd.read_csv(
            fn, delimiter=csv_delimiter, dtype=self._CSV_COLUMN_DATATYPES, engine="c"
        )

    def read_geoms(self, fn: Union[List[str], List[Path], str, Path]):
        """Read the Delft-FIAT exposure geoms.

        Parameters
        ----------
        fn : Union[List[str], List[Path], str, Path]
            One or multiple paths to the exposure geoms.
        """
        if isinstance(fn, str) or isinstance(fn, Path):
            fn = [fn]

        for f in fn:
            self.set_geom_names(Path(f).stem)
            self.set_exposure_geoms(gpd.read_file(f, engine="pyogrio"))

    def setup_buildings_from_single_source(
        self,
        source: Union[str, Path],
        ground_floor_height: Union[int, float, str, Path, None],
        extraction_method: str,
        ground_elevation_file: Union[int, float, str, Path, None] = None,
    ) -> None:
        """Set up asset locations and other available data from a single source.

        Parameters
        ----------
        source : Union[str, Path]
            The name of the vector dataset in the HydroMT Data Catalog or path to the
            vector dataset to be used to set up the asset locations. This can be either
            a point or polygon dataset.
        ground_floor_height : Union[int, float, str, Path, None]
            Either a number (int or float), to give all assets the same ground floor
            height or a path to the data that can be used to add the ground floor
            height to the assets.
        extraction_method : str
            The extraction method to be used for all of the assets.
        """
        if str(source).upper() == "NSI":
            # The NSI data is selected, so get the assets from the NSI
            self.logger.info(
                "Downloading assets from the National Structure Inventory."
            )
            polygon = self.region["geometry"].iloc[0]
            source_data = get_assets_from_nsi(self.data_catalog["NSI"].path, polygon)
        else:
            source_data = self.data_catalog.get_geodataframe(source, geom=self.region)

        if source_data.empty:
            self.logger.warning(
                f"No assets found in the selected region from source {source}."
            )

        # Set the CRS of the exposure data
        source_data_authority = source_data.crs.to_authority()
        self.crs = source_data_authority[0] + ":" + source_data_authority[1]

        # Read the json file that holds a dictionary of names of the source_data coupled
        # to Delft-FIAT names
        with open(
            self.data_catalog.get_source(source).driver_kwargs["translation_fn"]
        ) as json_file:
            attribute_translation_to_fiat = json_file.read()
        attribute_translation_to_fiat = json.loads(attribute_translation_to_fiat)

        # Fill the exposure data
        columns_to_fill = attribute_translation_to_fiat.keys()
        for column_name in columns_to_fill:
            try:
                assert attribute_translation_to_fiat[column_name] in source_data.columns
                self.exposure_db[column_name] = source_data[
                    attribute_translation_to_fiat[column_name]
                ]
            except AssertionError:
                self.logger.warning(
                    f"Attribute {attribute_translation_to_fiat[column_name]} not "
                    f"found in {str(source)}, skipping attribute."
                )

        # Check if the 'Object ID' column is unique
        if len(self.exposure_db.index) != len(set(self.exposure_db["Object ID"])):
            self.exposure_db["Object ID"] = range(1, len(self.exposure_db.index) + 1)

        # Set the ground floor height if not yet set
        if ground_floor_height != source:
            self.setup_ground_floor_height(ground_floor_height)

        # Set the extraction method
        self.setup_extraction_method(extraction_method)

        # Set the exposure_geoms
        self.set_exposure_geoms(
            gpd.GeoDataFrame(self.exposure_db[["Object ID", "geometry"]], crs=self.crs)
        )

        # Set the name to the geom_names
        self.set_geom_names("buildings")

        # Set the ground floor height if not yet set
        # TODO: Check a better way to access to to the geometries, self.empousure_geoms is a list an not a geodataframe
        if ground_elevation_file is not None:
            self.setup_ground_elevation(
                ground_elevation_file,
            )

        # Remove the geometry column from the exposure_db
        if "geometry" in self.exposure_db:
            del self.exposure_db["geometry"]

    def setup_roads(
        self,
        source: Union[str, Path],
        road_damage: Union[str, Path, int],
        road_types: Union[str, List[str], bool] = True,
    ):
        self.logger.info("Setting up roads...")
        if str(source).upper() == "OSM":
            polygon = self.region["geometry"].values[
                0
            ]  # TODO check if this works each time
            roads = get_roads_from_osm(polygon, road_types)

            if roads.empty:
                self.logger.warning(
                    "No roads found in the selected region from source " f"{source}."
                )

            # Rename the columns to FIAT names
            roads.rename(
                columns={"highway": "Secondary Object Type", "name": "Object Name"},
                inplace=True,
            )

            # Add an Object ID
            roads["Object ID"] = range(1, len(roads.index) + 1)
        else:
            roads = self.data_catalog.get_geodataframe(source, geom=self.region)
            # add the function to segmentize the roads into certain segments

        # Add the Primary Object Type and damage function, which is currently not set up to be flexible
        roads["Primary Object Type"] = "roads"
        roads["Damage Function: Structure"] = "roads"

        self.logger.info(
            "The damage function 'roads' is selected for all of the structure damage to the roads."
        )

        if isinstance(road_damage, str):
            # Add the max potential damage and the length of the segments to the roads
            road_damage = self.data_catalog.get_dataframe(road_damage)
            roads[
                ["Max Potential Damage: Structure", "Segment Length [m]"]
            ] = get_max_potential_damage_roads(roads, road_damage)
        elif isinstance(road_damage, int):
            roads["Segment Length [m]"] = get_road_lengths(roads)
            roads["Max Potential Damage: Structure"] = road_damage

        self.set_exposure_geoms(roads[["Object ID", "geometry"]])
        self.set_geom_names("roads")

        del roads["geometry"]

        # Update the exposure_db
        self.exposure_db = pd.concat([self.exposure_db, roads]).reset_index(drop=True)

    def setup_buildings_from_multiple_sources(
        self,
        asset_locations: Union[str, Path],
        occupancy_source: Union[str, Path],
        max_potential_damage: Union[str, Path],
        ground_floor_height: Union[int, float, str, Path, None],
        extraction_method: str,
        occupancy_attr: Union[str, None] = None,
        damage_types: Union[List[str], None] = None,
        country: Union[str, None] = None,
        attribute_name: Union[str, List[str], None] = None,
        gfh_method: Union[str, List[str], None] = "nearest",
        max_dist: Union[int, float,List[float], List[int], None] = 10,
        ground_elevation_file: Union[int, float, str, Path, None] = None,
    ):
        self.logger.info("Setting up exposure data from multiple sources...")
        self.setup_asset_locations(asset_locations)
        self.setup_occupancy_type(occupancy_source, occupancy_attr)
        self.setup_max_potential_damage(max_potential_damage, damage_types, country)
        self.setup_ground_floor_height(
            ground_floor_height, attribute_name, gfh_method, max_dist
        )
        self.setup_extraction_method(extraction_method)
        self.setup_ground_elevation(ground_elevation_file)

    def setup_asset_locations(self, asset_locations: str) -> None:
        """Set up the asset locations (points or polygons).

        Parameters
        ----------
        asset_locations : str
            The name of the vector dataset in the HydroMT Data Catalog or path to the
            vector dataset to be used to set up the asset locations. This can be either
            a point or polygon dataset.
        """
        self.logger.info("Setting up asset locations...")
        if str(asset_locations).upper() == "OSM":
            polygon = self.region.iloc[0].values[0]
            assets = get_assets_from_osm(polygon)

            if assets.empty:
                self.logger.warning(
                    "No assets found in the selected region from source "
                    f"{asset_locations}."
                )

            # Rename the osmid column to Object ID
            assets.rename(columns={"osmid": "Object ID"}, inplace=True)
        else:
            assets = self.data_catalog.get_geodataframe(
                asset_locations, geom=self.region
            )

        # Set the CRS of the exposure data
        self.crs = get_crs_str_from_gdf(assets.crs)

        # Check if the 'Object ID' column exists and if so, is unique
        if "Object ID" not in assets.columns:
            assets["Object ID"] = range(1, len(assets.index) + 1)
        else:
            if len(assets.index) != len(set(assets["Object ID"])):
                assets["Object ID"] = range(1, len(assets.index) + 1)

        # Set the asset locations to the geometry variable (self.exposure_geoms)
        # and set the geom name
        self.set_exposure_geoms(assets)
        self.set_geom_names("buildings")

    def set_geom_names(self, name: str) -> None:
        """Append a name to the list of geometry names `geom_names`."""
        self.logger.info(f"Setting geometry name to {name}...")
        self._geom_names.append(name)

    @property
    def geom_names(self) -> List[str]:
        """Returns a list with the geom names."""
        if len(self._geom_names) > 0 and len(self.exposure_geoms) > 0:
            return self._geom_names
        elif len(self._geom_names) == 0 and len(self.exposure_geoms) == 1:
            return ["exposure"]
        else:
            self.logger.warning(
                "No geometry names found, returning a list with the default names "
                "'exposure_X'."
            )
            return [f"exposure_{i}" for i in range(len(self.exposure_geoms))]

    def set_exposure_geoms(self, gdf: gpd.GeoDataFrame) -> None:
        """Append a GeoDataFrame to the exposure geometries `exposure_geoms`."""
        self.logger.info("Setting exposure geometries...")
        self.exposure_geoms.append(gdf)

    def setup_occupancy_type(
        self,
        occupancy_source: str,
        occupancy_attr: str,
        type_add: str = "Primary Object Type",
    ) -> None:
        self.logger.info(f"Setting up occupancy type from {str(occupancy_source)}...")
        if str(occupancy_source).upper() == "OSM":
            occupancy_map = self.setup_occupancy_type_from_osm()
            occupancy_types = ["Primary Object Type", "Secondary Object Type"]
        else:
            occupancy_map = self.data_catalog.get_geodataframe(
                occupancy_source, geom=self.region
            )
            occupancy_map.rename(columns={occupancy_attr: type_add}, inplace=True)
            occupancy_types = [type_add]

        # Check if the CRS of the occupancy map is the same as the exposure data
        if occupancy_map.crs != self.crs:
            occupancy_map = occupancy_map.to_crs(self.crs)
            self.logger.warning(
                "The CRS of the occupancy map is not the same as that "
                "of the exposure data. The occupancy map has been "
                f"reprojected to the CRS of the exposure data ({self.crs}) before "
                "doing the spatial join."
            )

        to_keep = ["geometry"] + occupancy_types

        # Spatially join the exposure data with the occupancy map
        if len(self.exposure_geoms) == 1:
            # If there is only one exposure geom, do the spatial join with the
            # occupancy_map. Only take the largest overlapping object from the
            # occupancy_map.
            gdf = sjoin_largest_area(self.exposure_geoms[0], occupancy_map[to_keep])

            # Remove the objects that do not have a Primary Object Type, that were not
            # overlapping with the land use map, or that had a land use type of 'nan'.
            nr_without_primary_object_type = len(
                gdf.loc[gdf["Primary Object Type"] == ""].index
            )
            if nr_without_primary_object_type > 0:
                self.logger.warning(
                    f"{nr_without_primary_object_type} objects do not have a Primary Object "
                    "Type and will be removed from the exposure data."
                )
            gdf = gdf.loc[gdf["Primary Object Type"] != ""]

            nr_without_landuse = len(gdf.loc[gdf["Primary Object Type"].isna()].index)
            if nr_without_landuse > 0:
                self.logger.warning(
                    f"{nr_without_landuse} objects were not overlapping with the "
                    "land use data and will be removed from the exposure data."
                )
            gdf = gdf.loc[gdf["Primary Object Type"].notna()]

            # Update the exposure geoms
            self.exposure_geoms[0] = gdf[["Object ID", "geometry"]]

            # Remove the geometry column from the exposure database
            del gdf["geometry"]
            # Update the exposure database
            if type_add in self.exposure_db:
                gdf.rename(columns={"Primary Object Type": "pot"}, inplace=True)
                self.exposure_db = pd.merge(
                    self.exposure_db, gdf, on="Object ID", how="left"
                )
                self.exposure_db = self._set_values_from_other_column(
                    self.exposure_db, "Primary Object Type", "pot"
                )
            else:
                self.exposure_db = gdf.copy()
        else:
            self.logger.warning(
                "NotImplemented the spatial join of the exposure data with the "
                "occupancy map the for multiple exposure geoms"
            )
            NotImplemented

    def setup_occupancy_type_from_osm(self) -> None:
        # We assume that the OSM land use data contains an attribute 'landuse' that
        # contains the land use type.
        occupancy_attribute = "landuse"

        # Get the land use from OSM
        polygon = self.region.iloc[0][0]
        occupancy_map = get_landuse_from_osm(polygon)

        if occupancy_map.empty:
            self.logger.warning(
                "No land use data found in the selected region from source 'OSM'."
            )

        # Log the unique landuse types
        self.logger.info(
            "The following unique landuse types are found in the OSM data: "
            f"{list(occupancy_map[occupancy_attribute].unique())}"
        )

        # Map the landuse types to types used in the JRC global vulnerability curves
        # and the JRC global damage values
        landuse_to_jrc_mapping = {
            "commercial": "commercial",
            "construction": "",
            "fairground": "commercial",
            "industrial": "industrial",
            "residential": "residential",
            "retail": "commercial",
            "institutional": "commercial",
            "aquaculture": "",
            "allotments": "",  # TODO: add agriculture to the JRC curves and include "agriculture"
            "farmland": "",  # TODO: add agriculture to the JRC curves and include "agriculture"
            "farmyard": "",  # TODO: add agriculture to the JRC curves and include "agriculture"
            "animal_keeping": "",  # TODO: add agriculture to the JRC curves and include "agriculture"
            "flowerbed": "",
            "forest": "",
            "greenhouse_horticulture": "",  # TODO: add agriculture to the JRC curves and include "agriculture"
            "meadow": "",
            "orchard": "",  # TODO: add agriculture to the JRC curves and include "agriculture"
            "plant_nursery": "",  # TODO: add agriculture to the JRC curves and include "agriculture"
            "vineyard": "",  # TODO: add agriculture to the JRC curves and include "agriculture"
            "basin": "",
            "salt_pond": "",
            "grass": "",
            "brownfield": "",
            "cemetary": "",
            "depot": "",
            "garages": "",
            "greenfield": "",
            "landfill": "",
            "military": "",
            "port": "industrial",
            "quarry": "",
            "railway": "",
            "recreation_ground": "",
            "religious": "",
            "village_green": "",
            "winter_sports": "",
            "street": "",
        }

        occupancy_map["Primary Object Type"] = occupancy_map[occupancy_attribute].map(
            landuse_to_jrc_mapping
        )
        occupancy_map.rename(
            columns={occupancy_attribute: "Secondary Object Type"}, inplace=True
        )

        return occupancy_map

    def setup_extraction_method(self, extraction_method: str) -> None:
        self.exposure_db["Extraction Method"] = extraction_method

    def setup_aggregation_labels(self):
        NotImplemented

    @staticmethod
    def intersection_method(
            gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """If the selected method is "intersection"  the intersection method duplicates columns if they have the same name in the geodataframe 
        provided by the user and the original exposure_db. Newly added columns by the method are dropped 
        and/or renamed and placed in the correct order of the exposure_db.  

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            The geodataframe after the spatial joint of the user input data and the exposure_db. 
        """
        duplicate_columns_left = [col for col in gdf.columns if col.endswith("_left")]
        if duplicate_columns_left:
            for item in duplicate_columns_left:
                exposure_db_name = item.rstrip("_left")
                position = gdf.columns.get_loc(item)
                gdf.insert(position, exposure_db_name, gdf[item])
                del gdf[item]   
        return gdf  
    
    def setup_ground_floor_height(
        self,
        ground_floor_height: Union[int, float, None, str, Path, List[str], List[Path]],
        attribute_name: Union[str, List[str], None] = None,
        gfh_method: Union[str, List[str], None] = "nearest",
        max_dist: float = 10,
    ) -> None:
        """Set the ground floor height of the exposure data. This function overwrites
        the existing Ground Floor Height column if it already exists.

        Parameters
        ----------
        ground_floor_height : Union[int, float, None, str, Path, List[str], List[Path]]
            A number to set the Ground Floor Height of all assets to the same value, a
            path to a file that contains the Ground Floor Height of each asset, or a
            list of paths to files that contain the Ground Floor Height of each asset,
            in the order of preference (the first item in the list gets the highest
            priority in assigning the values).
        attribute_name : Union[str, List[str]], optional
            The name of the attribute that contains the Ground Floor Height in the
            file(s) that are submitted. If multiple `ground_floor_height` files are
            submitted, the attribute names are linked to the files in the same order as
            the files are submitted. By default None.
        gfh_method : Union[str, List[str]], optional
            The method to use to assign the Ground Floor Height to the assets. If
            multiple `ground_floor_height` files are submitted, the methods are linked
            to the files in the same order as the files are submitted. The method can
            be either 'nearest' (nearest neighbor) or 'intersection'. By default
            'nearest'.
        max_dist : float
            The maximum distance for the nearest join measured in meters, by default
            set to 10 meters.
        """
        if ground_floor_height:
            if isinstance(ground_floor_height, int) or isinstance(
                ground_floor_height, float
            ):
                # If the Ground Floor Height is input as a number, assign all objects with
                # the same Ground Floor Height.
                self.exposure_db["Ground Floor Height"] = ground_floor_height
            elif isinstance(ground_floor_height, str) or isinstance(
                ground_floor_height, Path
            ):
                # A single file is used to assign the ground floor height to the assets
                gfh = self.data_catalog.get_geodataframe(ground_floor_height)
                gdf = self.get_full_gdf(self.exposure_db)
                gdf = join_spatial_data(
                    gdf, gfh, attribute_name, gfh_method, max_dist, self.logger
                )
                self.exposure_db = self._set_values_from_other_column(
                    gdf, "Ground Floor Height", attribute_name
                )
                if "geometry" in self.exposure_db.columns:
                    self.exposure_db.drop(columns=["geometry"], inplace=True)
                
            elif isinstance(ground_floor_height, list):
                # Multiple files are used to assign the ground floor height to the assets
                NotImplemented
        else:
            # Set the Ground Floor Height to 0 if the user did not specify any
            # Ground Floor Height.
            self.exposure_db["Ground Floor Height"] = 0

    def setup_max_potential_damage(
        self,
        max_potential_damage: Union[
            int, float, str, Path, List[str], List[Path], pd.DataFrame
        ] = None,
        damage_types: Union[List[str], str, None] = None,
        attribute_name: Union[str, List[str], None] = None,
        method_damages: Union[str, List[str], None] = "nearest",
        max_dist: float = 10,
        country: Union[str, None] = None,
    ) -> None:
        """Setup the max potential damage column of the exposure data in various ways.

        Parameters
        ----------
        max_potential_damage : Union[int, float, str, Path, List[str], List[Path], pd.DataFrame], optional
            _description_, by default None
        damage_types : Union[List[str], str, None], optional
            _description_, by default None
        country : Union[str, None], optional
            _description_, by default None
        attribute_name : Union[str, List[str], None], optional
            _description_, by default None
        method_damages : Union[str, List[str], None], optional
            _description_, by default "nearest"
        max_dist : float, optional
            _description_, by default 10
        """
        if damage_types is None:
            damage_types = ["total"]

        if isinstance(damage_types, str):
            damage_types = [damage_types]

        if isinstance(max_potential_damage, pd.DataFrame):
            self.update_max_potential_damage(
                updated_max_potential_damages=max_potential_damage
            )
        elif isinstance(max_potential_damage, int) or isinstance(
            max_potential_damage, float
        ):
            # Set the column(s) to a single value
            for damage_type in damage_types:
                self.exposure_db[
                    f"Max Potential Damage: {damage_type}"
                ] = max_potential_damage

        elif isinstance(max_potential_damage, list):
            # Multiple files are used to assign the ground floor height to the assets
            count = 0
            for i in max_potential_damage:
                # When the max_potential_damage is a string but not jrc_damage_values
                # or hazus_max_potential_damages. Here, a single file is used to
                # assign the ground floor height to the assets
                gfh = self.data_catalog.get_geodataframe(i)

                # If method is "intersection" remove columns from gfh exept for attribute name and geometry
                if method_damages[count] == "intersection":
                    columns_to_drop = [col for col in gfh.columns if col != attribute_name[count] and col != "geometry"]
                    gfh = gfh.drop(columns=columns_to_drop)
                
                # Get exposure data
                gdf = self.get_full_gdf(self.exposure_db)
                
                # Spatial joint of damage data (user input) and exposure data 
                gdf = join_spatial_data(gdf, gfh, attribute_name[count], method_damages[count], max_dist[count], self.logger)

                # If method is "intersection" rename *"_left" to original exposure_db name 
                if method_damages[count] == "intersection":
                    self.intersection_method(gdf) 

                # Update exposure_db with updated dataframe
                self.exposure_db = self._set_values_from_other_column(
                    gdf, f"Max Potential Damage: {damage_types[count].capitalize()}", attribute_name[count]
                )
                if "geometry" in self.exposure_db.columns:
                    self.exposure_db.drop(columns=["geometry"], inplace=True)
                count +=1
            
        elif max_potential_damage in [
            "jrc_damage_values",
            "hazus_max_potential_damages",
        ]:
            if max_potential_damage == "jrc_damage_values":
                damage_source = self.data_catalog.get_dataframe(max_potential_damage)
                if country is None:
                    country = "World"
                    self.logger.warning(
                        f"No country specified, using the '{country}' JRC damage values."
                    )

                damage_values = preprocess_jrc_damage_values(damage_source, country)

            elif max_potential_damage == "hazus_max_potential_damages":
                damage_source = self.data_catalog.get_dataframe(max_potential_damage)
                damage_values = preprocess_hazus_damage_values(damage_source)

            # Calculate the area of each object
            gdf = self.get_full_gdf(self.exposure_db)[
                ["Primary Object Type", "geometry"]
            ]
            gdf = get_area(gdf)

            # Set the damage values to the exposure data
            for damage_type in damage_types:
                # Calculate the maximum potential damage for each object and per damage type
                try:
                    self.exposure_db[
                        f"Max Potential Damage: {damage_type.capitalize()}"
                    ] = [
                        damage_values[building_type][damage_type.lower()]
                        * square_meters
                        for building_type, square_meters in zip(
                            gdf["Primary Object Type"], gdf["area"]
                        )
                    ]
                except KeyError as e:
                    self.logger.warning(
                        f"Not found in the {max_potential_damage} damage "
                        f"value data: {e}"
                    )
        elif isinstance(max_potential_damage, str) or isinstance(
            max_potential_damage, Path
        ):
            # When the max_potential_damage is a string but not jrc_damage_values
            # or hazus_max_potential_damages. Here, a single file is used to
            # assign the ground floor height to the assets
            gfh = self.data_catalog.get_geodataframe(max_potential_damage)
            gdf = self.get_full_gdf(self.exposure_db)
            gdf = join_spatial_data(gdf, gfh, attribute_name, method_damages, max_dist, self.logger)
            self.exposure_db = self._set_values_from_other_column(
                gdf, f"Max Potential Damage: {damage_types[0].capitalize()}", attribute_name
            )

    def setup_ground_elevation(
        self,
        ground_elevation: Union[int, float, None, str, Path],
    ) -> None:
        if ground_elevation:
            self.exposure_db["Ground Elevation"] = ground_elevation_from_dem(
                ground_elevation=ground_elevation,
                exposure_db=self.exposure_db,
                exposure_geoms=self.get_full_gdf(self.exposure_db),
            )

        else:
            print(
                "Ground elevation is not recognized by the setup_ground_elevation function\n Ground elevation will be set to 0"
            )
            self.exposure_db["Ground Elevation"] = 0

    def update_max_potential_damage(
        self, updated_max_potential_damages: pd.DataFrame
    ) -> None:
        """Updates the maximum potential damage columns that are provided in a
        Pandas DataFrame.

        Parameters
        ----------
        updated_max_potential_damages : pd.DataFrame
            A DataFrame containing the values of the maximum potential damage that
            should be updated.
        """
        self.logger.info(
            f"Updating the maximum potential damage of {len(updated_max_potential_damages.index)} properties."
        )
        if "Object ID" not in updated_max_potential_damages.columns:
            self.logger.warning(
                "Trying to update the maximum potential damages but no 'Object ID' column is found in the updated_max_potential_damages variable."
            )
            return

        damage_cols = [
            c
            for c in updated_max_potential_damages.columns
            if "Max Potential Damage:" in c
        ]
        updated_max_potential_damages.sort_values("Object ID", inplace=True)
        self.exposure_db.sort_values("Object ID", inplace=True)

        self.exposure_db.loc[
            self.exposure_db["Object ID"].isin(
                updated_max_potential_damages["Object ID"]
            ),
            damage_cols,
        ] = updated_max_potential_damages[damage_cols]

    def raise_ground_floor_height(
        self,
        raise_by: Union[int, float],
        objectids: List[int],
        height_reference: str = "",
        path_ref: str = None,
        attr_ref: str = "STATIC_BFE",
    ):
        """Raises the ground floor height of selected objects to a certain level.

        Parameters
        ----------
        raise_by : Union[int, float]
            The level to raise the selected objects by.
        objectids : List[int]
            A list of Object IDs to select the exposure objects to raise the ground
            floor of.
        height_reference : str, optional
            Either 'datum' when the Ground Floor Height should be raised relative to the
            Datum or 'geom' when the Ground Floor Height should be raised relative to
            the attribute `attr_ref` in the geometry file `path_ref`, by default ""
        path_ref : str, optional
            The full path to the geometry file used to calculate the Ground Floor
            Height if the `height_reference` is set 'geom', by default None
        attr_ref : str, optional
            The attribute in the geometry file `path_ref`, by default "STATIC_BFE"
        """
        # ground floor height attr already exist, update relative to a reference file or datum
        # Check if the Ground Floor Height column already exists
        if "Ground Floor Height" not in self.exposure_db.columns:
            self.logger.warning(
                "Trying to update the Ground Floor Height but the attribute does not "
                "yet exist in the exposure data."
            )
            return

        # Get the index of the objects to raise the ground floor height.
        idx = self.exposure_db.loc[self.exposure_db["Object ID"].isin(objectids)].index

        # Log the number of objects that are being raised.
        self.logger.info(
            f"Raising the ground floor height of {len(idx)} properties to {raise_by}."
        )  # TODO: add the unit of the ground floor height

        if height_reference.lower() == "datum":
            # Elevate the object with 'raise_to'
            self.logger.info(
                "Raising the ground floor height of the properties relative to Datum."
            )
            self.exposure_db.loc[
                (self.exposure_db["Ground Floor Height"] < raise_by)
                & self.exposure_db.index.isin(idx),
                "Ground Floor Height",
            ] = raise_by

        elif height_reference.lower() in ["geom", "table"]:
            # Elevate the objects relative to the surface water elevation map that the
            # user submitted.
            self.logger.info(
                "Raising the ground floor height of the properties relative to "
                f"{Path(path_ref).name}, with column {attr_ref}."
            )

            if len(self.exposure_geoms) == 0:
                self.set_exposure_geoms_from_xy()

            self.exposure_db.iloc[idx, :] = self.set_height_relative_to_reference(
                self.exposure_db.iloc[idx, :],
                self.exposure_geoms[0].iloc[idx, :],
                height_reference,
                path_ref,
                attr_ref,
                raise_by,
                self.crs,
            )
            self.logger.info(
                "set_height_relative_to_reference can for now only be used for the "
                "original exposure data."
            )

        else:
            self.logger.warning(
                "The height reference of the Ground Floor Height is set to "
                f"'{height_reference}'. "
                "This is not one of the allowed height references. Set the height "
                "reference to 'datum', 'geom' or 'raster' (last option not yet "
                "implemented)."
            )

    def truncate_damage_function(
        self,
        objectids: List[int],
        floodproof_to: Union[int, float],
        damage_function_types: List[str],
        vulnerability: Vulnerability,
    ) -> None:
        """Truncates damage functions to a certain level.

        Parameters
        ----------
        objectids : List[int]
            A list of Object IDs to select the exposure objects to truncate the damage
            functions of.
        floodproof_to : Union[int, float]
            The height to floodproof to, i.e. to truncate the damage functions to.
        damage_function_types : List[str]
            A list of damage types that should be considered for the new composite area,
            e.g. ['Structure', 'Content']. The function is case-sensitive.
        vulnerability : Vulnerability
            The Vulnerability object from the FiatModel.
        """
        self.logger.info(
            f"Floodproofing {len(objectids)} properties for {floodproof_to} "
            f"{vulnerability.unit} of water."
        )

        # The user can submit with how much feet the properties should be floodproofed
        # and the damage function is truncated to that level.
        df_name_suffix = f'_fp_{str(floodproof_to).replace(".", "_")}'

        ids = self.get_object_ids(selection_type="list", objectids=objectids)
        idx = self.exposure_db.loc[self.exposure_db["Object ID"].isin(ids)].index

        # Find all damage functions that should be modified and truncate with
        # floodproof_to.
        for df_type in damage_function_types:
            dfs_to_modify = [
                d
                for d in list(
                    self.exposure_db.iloc[idx, :][
                        f"Damage Function: {df_type}"
                    ].unique()
                )
                if d == d
            ]
            if dfs_to_modify:
                for df_name in dfs_to_modify:
                    vulnerability.truncate(
                        damage_function_name=df_name,
                        suffix=df_name_suffix,
                        floodproof_to=floodproof_to,
                    )

        # Rename the damage function names in the exposure data file
        damage_function_column_idx = [
            self.exposure_db.columns.get_loc(c)
            for c in self.get_damage_function_columns()
            if c.split(": ")[-1] in damage_function_types
        ]
        self.exposure_db.iloc[idx, damage_function_column_idx] = (
            self.exposure_db.iloc[idx, damage_function_column_idx] + df_name_suffix
        )

    def calculate_damages_new_exposure_object(
        self, percent_growth: float, damage_types: List[str]
    ):
        damages_cols = [
            c
            for c in self.get_max_potential_damage_columns()
            if c.split("Max Potential Damage: ")[-1] in damage_types
        ]
        new_damages = dict()

        # Calculate the Max. Potential Damages for the new area. This is the total
        # percentage of population growth multiplied with the total sum of the Max
        # Potential Structural/Content/Other Damage.
        for c in damages_cols:
            total_damages = sum(self.exposure_db[c].fillna(0))
            new_damages[c.split("Max Potential Damage: ")[-1]] = (
                total_damages * percent_growth
            )

        return new_damages

    def setup_new_composite_areas(
        self,
        percent_growth: float,
        geom_file: str,
        ground_floor_height: float,
        damage_types: List[str],
        vulnerability: Vulnerability,
        elevation_reference: str,
        path_ref: str = None,
        attr_ref: str = None,
        ground_elevation: Union[None, str, Path] = None,
        aggregation_area_fn: Union[List[str], List[Path], str, Path] = None,
        attribute_names: Union[List[str], str] = None,
        label_names: Union[List[str], str] = None,
    ) -> None:
        """Adds one or multiple (polygon) areas to the exposure database with
        a composite damage function and a percentage of the total damage.

        Parameters
        ----------
        percent_growth : float
            The percent of the total damages that should be divided over the new
            composite area(s) per damage type in `damage_types`.
        geom_file : str
            The full path to the file that contains the geometries of composite areas.
            Optionally this file can contain a feature 'FID' to link to the exposure
            database.
        ground_floor_height : float
            The height that the ground floor should have relative to either 'datum' or
            'geom' as defined in the `elevation_reference` variable.
        damage_types : List[str]
            A list of damage types that should be considered for the new composite area,
            e.g. ['Structure', 'Content']. The function is case-sensitive.
        vulnerability : Vulnerability
            The Vulnerability object from the FiatModel.
        elevation_reference : str
            Either 'datum' when the Ground Floor Height should be set relative to the
            Datum or 'geom' when the Ground Floor Height should be set relative to the
            attribute `attr_ref` in the geometry file `path_ref`.
        path_ref : str, optional
            The full path to the geometry file used to calculate the Ground Floor
            Height if the `elevation_reference` is set 'geom', by default None
        attr_ref : str, optional
            The attribute in the geometry file `path_ref`, by default None
        """
        self.logger.info(
            f"Adding a new exposure object with a value of {percent_growth}% "
            "of the current total exposure objects, using the "
            f"geometry/geometries from {geom_file}."
        )

        percent_growth = float(percent_growth) / 100
        geom_file = Path(geom_file)
        assert (
            geom_file.is_file()
        ), f"File {str(geom_file)} is missing, cannot set up a new composite area."

        # Calculate the total damages for the new object, for the indicated damage types
        new_object_damages = self.calculate_damages_new_exposure_object(
            percent_growth, damage_types
        )

        # Read the original damage functions and create new weighted damage functions
        # from the original ones.
        df_dict = {
            damage_type: [
                df
                for df in self.exposure_db["Damage Function: " + damage_type].unique()
                if df == df
            ]
            for damage_type in damage_types
        }
        df_value_counts_dict = {
            damage_type: self.exposure_db[
                "Damage Function: " + damage_type
            ].value_counts()
            for damage_type in damage_types
        }
        new_damage_functions = vulnerability.calculate_weighted_damage_function(
            df_dict, df_value_counts_dict
        )

        # Add the new development area as an object to the Exposure Modification file.
        new_area = gpd.read_file(geom_file, engine="pyogrio")
        # check_crs(new_area, geom_file)  #TODO implement again
        new_objects = []

        # Calculate the total area to use for adding the damages relative to area
        total_area = (
            new_area.geometry.area.sum()
        )  # TODO: reproject to a projected CRS if this is a geographic CRS?

        # There should be an attribute 'Object ID' in the new development area shapefile.
        # This ID is used to join the shapefile to the exposure data.
        join_id_name = "Object ID"
        if join_id_name not in new_area.columns:
            self.logger.debug(
                'The unique ID column in the New Development Area is not named "Object ID", '
                'therefore, a new unique identifyer named "Object ID" is added.'
            )
            new_area[join_id_name] = range(len(new_area.index))

        max_id = self.exposure_db["Object ID"].max()
        new_geoms_ids = []
        for i in range(len(new_area.index)):
            new_geom = new_area.geometry.iloc[i]
            new_id = max_id + 1

            perc_damages = new_geom.area / total_area
            # Alert the user that the ground elevation is set to 0.
            # TODO: Take ground elevation from DEM?
            # For water level calculation this will not take into account the
            # non-flooded cells separately, just averaged over the whole area.
            self.logger.warning(
                "The ground elevation is set to 0 if no DEM is supplied."
            )

            # Idea: Reduction factor for the part of the area is not build-up?

            dict_new_objects_data = {
                "Object ID": [new_id],
                "Object Name": ["New development area: " + str(new_id)],
                "Primary Object Type": ["New development area"],
                "Secondary Object Type": ["New development area"],
                "Extraction Method": ["area"],
                "Ground Floor Height": [0],
                "Ground Elevation": [0],
            }
            dict_new_objects_data.update(
                {
                    f"Damage Function: {damage_type}": [
                        new_damage_functions[damage_type]
                    ]
                    for damage_type in damage_types
                }
            )
            dict_new_objects_data.update(
                {
                    f"Max Potential Damage: {damage_type}": [
                        new_object_damages[damage_type] * perc_damages
                    ]
                    for damage_type in damage_types
                }
            )
            new_objects.append(pd.DataFrame(dict_new_objects_data))
            new_geoms_ids.append((new_geom, new_id))
            max_id += 1

        # Make one DataFrame from the list of new object DataFrames
        new_objects = pd.concat(new_objects)
        new_objects.reset_index(inplace=True, drop=True)

        # Create a new GeoDataFrame with the new geometries and the Object ID
        _new_exposure_geoms = gpd.GeoDataFrame(
            data=new_geoms_ids, columns=["geometry", "Object ID"], crs=self.crs
        )

        if elevation_reference == "datum":
            new_objects["Ground Floor Height"] = ground_floor_height
            self.logger.info(
                f"The elevation of the new development area is {ground_floor_height} ft"
                " relative to datum."  # TODO: make unit flexible
            )
        elif elevation_reference == "geom":
            self.logger.info(
                f"The elevation of the new development area is {ground_floor_height} ft"
                f" relative to {Path(path_ref).stem}. The height of the floodmap is"
                f" identified with column {attr_ref}."  # TODO: make unit flexible
            )
            new_objects = self.set_height_relative_to_reference(
                new_objects,
                _new_exposure_geoms,
                elevation_reference,
                path_ref,
                attr_ref,
                ground_floor_height,
                self.crs,
            )

        # Update the exposure_geoms
        self.set_geom_names("new_development_area")
        self.set_exposure_geoms(_new_exposure_geoms)

        # If the user supplied ground elevation data, assign that to the new
        # composite areas
        if ground_elevation is not None:
            new_objects["Ground Elevation"] = ground_elevation_from_dem(
                ground_elevation=ground_elevation,
                exposure_db=new_objects,
                exposure_geoms=_new_exposure_geoms,
            )

        # If the user supplied aggregation area data, assign that to the
        # new composite areas
        if aggregation_area_fn is not None:
            new_objects = join_exposure_aggregation_areas(
                _new_exposure_geoms.merge(new_objects, on="Object ID"),
                aggregation_area_fn=aggregation_area_fn,
                attribute_names=attribute_names,
                label_names=label_names,
            )

        # Update the exposure_db
        self.exposure_db = pd.concat([self.exposure_db, new_objects]).reset_index(
            drop=True
        )

    def link_exposure_vulnerability(
        self,
        exposure_linking_table: pd.DataFrame,
        damage_types: Optional[List[str]] = ["Structure", "Content"],
    ):
        exposure_linking_table["Damage function name"] = [
            name + "_" + type
            for name, type in zip(
                exposure_linking_table["FIAT Damage Function Name"].values,
                exposure_linking_table["Damage Type"].values,
            )
        ]
        for damage_type in damage_types:
            linking_per_damage_type = exposure_linking_table.loc[
                exposure_linking_table["Damage Type"] == damage_type, :
            ]
            assert (
                not linking_per_damage_type.empty
            ), f"Damage type {damage_type} not found in the exposure-vulnerability linking table"

            # Create a dictionary that links the exposure data to the vulnerability data
            linking_dict = dict(
                zip(
                    linking_per_damage_type["Exposure Link"],
                    linking_per_damage_type["Damage function name"],
                )
            )
            unique_linking_types = set(linking_dict.keys())

            # Find the column to link the exposure data to the vulnerability data
            unique_types_primary = set()

            # Set the variables below to large numbers to ensure when there is no
            # Primary Object Type or Secondary Object Type column in the exposure data
            # that the available column is used to link the exposure data to the
            # vulnerability data.
            len_diff_primary_linking_types = 100000
            len_diff_secondary_linking_types = 100000
            if "Primary Object Type" in self.exposure_db.columns:
                unique_types_primary = set(self.get_primary_object_type())
                diff_primary_linking_types = unique_types_primary - unique_linking_types
                len_diff_primary_linking_types = len(diff_primary_linking_types)

            unique_types_secondary = set()
            if "Secondary Object Type" in self.exposure_db.columns:
                unique_types_secondary = set(self.get_secondary_object_type())
                diff_secondary_linking_types = (
                    unique_types_secondary - unique_linking_types
                )
                len_diff_secondary_linking_types = len(diff_secondary_linking_types)

            # Check if the linking column is the Primary Object Type or the Secondary
            # Object Type
            if (len(unique_types_primary) > 0) and (
                unique_types_primary.issubset(unique_linking_types)
            ):
                linking_column = "Primary Object Type"
            elif (len(unique_types_secondary) > 0) and (
                unique_types_secondary.issubset(unique_linking_types)
            ):
                linking_column = "Secondary Object Type"
            else:
                if (
                    len_diff_primary_linking_types < len_diff_secondary_linking_types
                ) and (len(unique_types_primary) > 0):
                    linking_column = "Primary Object Type"
                    self.logger.warning(
                        "There are "
                        f"{str(len_diff_primary_linking_types)} primary"
                        " object types that are not in the linking "
                        "table and will not have a damage function "
                        f"assigned for {damage_type} damages: "
                        f"{str(list(diff_primary_linking_types))}"
                    )
                elif (
                    len_diff_secondary_linking_types < len_diff_primary_linking_types
                ) and (len(unique_types_secondary) > 0):
                    linking_column = "Secondary Object Type"
                    self.logger.warning(
                        "There are "
                        f"{str(len(diff_secondary_linking_types))} "
                        "secondary object types that are not in the "
                        "linking table and will not have a damage "
                        f"function assigned for {damage_type} damages: "
                        f"{str(list(diff_secondary_linking_types))}"
                    )

            self.exposure_db[
                f"Damage Function: {damage_type.capitalize()}"
            ] = self.exposure_db[linking_column].map(linking_dict)

            self.logger.info(
                f"The {linking_column} was used to link the exposure data to the "
                f"vulnerability curves for {damage_type} damages."
            )

    def get_primary_object_type(self):
        if "Primary Object Type" in self.exposure_db.columns:
            return list(self.exposure_db["Primary Object Type"].unique())

    def get_secondary_object_type(self):
        if "Secondary Object Type" in self.exposure_db.columns:
            return list(self.exposure_db["Secondary Object Type"].unique())

    def get_max_potential_damage_columns(self) -> List[str]:
        """Returns the maximum potential damage columns in <exposure_db>

        Returns
        -------
        List[str]
            The maximum potential damage columns in <exposure_db>
        """
        return [c for c in self.exposure_db.columns if "Max Potential Damage:" in c]

    def get_damage_function_columns(self) -> List[str]:
        """Returns the damage function columns in <exposure_db>

        Returns
        -------
        List[str]
            The damage function columns in <exposure_db>
        """
        return [c for c in self.exposure_db.columns if "Damage Function:" in c]

    def select_objects(
        self,
        primary_object_type: Optional[Union[str, List[str]]] = None,
        non_building_names: Optional[List[str]] = None,
        return_gdf: bool = False,
    ) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
        """Filters the Exposure Database by <primary_object_type> and
        <non_building_names>

        Parameters
        ----------
        primary_object_type : Optional[Union[str, List[str]]], optional
            Only select assets from this/these primary object type(s).
            Can be any primary object type in a list or 'all', by default None
            (also selecting all)
        non_building_names : Optional[list[str]], optional
            The names of the , by default None
        return_gdf : bool, optional
            If True the function returns a GeoDataFrame, if False the function
            returns a Dataframe, by default False

        Returns
        -------
        objects : Union[pd.DataFrame, gpd.GeoDataFrame]
            The filtered (Geo)DataFrame.
        """
        objects = self.exposure_db
        if return_gdf:
            objects = self.get_full_gdf(objects)

        if non_building_names:
            objects = objects.loc[
                ~objects["Primary Object Type"].isin(non_building_names), :
            ]

        if primary_object_type:
            if str(primary_object_type).lower() != "all":
                objects = objects.loc[
                    objects["Primary Object Type"].isin([primary_object_type]), :
                ]

        return objects

    def get_object_ids(
        self,
        selection_type: str,
        property_type: Optional[str] = None,
        non_building_names: Optional[List[str]] = None,
        aggregation: Optional[str] = None,
        aggregation_area_name: Optional[str] = None,
        polygon_file: Optional[str] = None,
        list_file: Optional[str] = None,
        objectids: Optional[List[int]] = None,
    ) -> list[Any]:
        """Get ids of objects that are affected by the measure.

        Parameters
        ----------
        selection_type : str
            Type of selection, either 'all', 'aggregation_area',
            'polygon', or 'list'.
        property_type : Optional[str], optional
            _description_, by default None
        non_building_names : Optional[List[str]], optional
            _description_, by default None
        aggregation : Optional[str], optional
            _description_, by default None
        aggregation_area_name : Optional[str], optional
            _description_, by default None
        polygon_file : Optional[str], optional
            _description_, by default None
        list_file : Optional[str], optional
            _description_, by default None
        objectids : Optional[List[int]], optional
            _description_, by default None

        Returns
        -------
        list[Any]
            list of ids
        """
        if (selection_type == "aggregation_area") or (selection_type == "all"):
            buildings = self.select_objects(
                primary_object_type=property_type,
                non_building_names=non_building_names,
            )
            if selection_type == "all":
                ids = buildings["Object ID"]
            elif selection_type == "aggregation_area":
                ids = buildings.loc[
                    buildings[f"Aggregation Label: {aggregation}"]
                    == aggregation_area_name,
                    "Object ID",
                ]
        elif selection_type == "polygon":
            assert polygon_file is not None
            buildings = self.select_objects(
                primary_object_type=property_type,
                non_building_names=non_building_names,
                return_gdf=True,
            )
            polygon = gpd.read_file(polygon_file, engine="pyogrio")
            ids = gpd.sjoin(buildings, polygon)["Object ID"]
        elif selection_type == "list":
            ids = objectids

        return list(ids)

    def set_exposure_geoms_from_xy(self):
        if not (
            self.exposure_db["X Coordinate"].isna().any()
            and self.exposure_db["Y Coordinate"].isna().any()
        ):
            exposure_geoms = gpd.GeoDataFrame(
                {
                    "Object ID": self.exposure_db["Object ID"],
                    "geometry": gpd.points_from_xy(
                        self.exposure_db["X Coordinate"],
                        self.exposure_db["Y Coordinate"],
                    ),
                },
                crs=self.crs,
            )
        self.set_exposure_geoms(exposure_geoms)

    def get_full_gdf(
        self, df: pd.DataFrame
    ) -> Union[gpd.GeoDataFrame, List[gpd.GeoDataFrame]]:
        # Create a copy from the dataframe to ensure the values are not changed in the
        # original dataframe
        df = df.copy()

        # Check how many exposure geoms there are
        if len(self.exposure_geoms) == 1:
            assert set(self.exposure_geoms[0]["Object ID"]) == set(df["Object ID"])
            df["geometry"] = self.exposure_geoms[0]["geometry"]
            gdf = gpd.GeoDataFrame(df, crs=self.exposure_geoms[0].crs)
        elif len(self.exposure_geoms) > 1:
            gdf_list = []
            for i in range(len(self.exposure_geoms)):
                gdf_list.append(
                    self.exposure_geoms[i].merge(df, on="Object ID", how="left")
                )
            gdf = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True))
        return gdf

    def check_required_columns(self):
        """Checks whether the <_REQUIRED_COLUMNS> are in the <exposure_db>."""
        for col in self._REQUIRED_COLUMNS:
            try:
                assert col in self.exposure_db.columns
            except AssertionError:
                print(f"Required column {col} not found in exposure data.")

        for col in self._REQUIRED_VARIABLE_COLUMNS:
            try:
                assert col.format("Structure") in self.exposure_db.columns
            except AssertionError:
                print(f"Required variable column {col} not found in exposure data.")

    def set_height_relative_to_reference(
        self,
        exposure_to_modify: pd.DataFrame,
        exposure_geoms: gpd.GeoDataFrame,
        height_reference: str,
        path_ref: str,
        attr_ref: str,
        raise_by: Union[int, float],
        out_crs: str,
    ) -> gpd.GeoDataFrame:
        """Sets the height of exposure_to_modify to the level of the reference file.

        Parameters
        ----------
        exposure_to_modify : pd.DataFrame
            _description_
        exposure_geoms : gpd.GeoDataFrame
            _description_
        height_reference : str
            _description_
        path_ref : str
            _description_
        attr_ref : str
            _description_
        raise_by : Union[int, float]
            _description_
        out_crs : _type_
            _description_

        Returns
        -------
        gpd.GeoDataFrame
            _description_

        Note: It is assumed that the datum/DEM with which the geom file is created is
        the same as that of the exposure data
        """
        # Add the different options of input data: vector, raster, table
        if height_reference == "geom":
            reference_shp = gpd.read_file(path_ref, engine="pyogrio")  # Vector

            # Reproject the input flood map if necessary
            if reference_shp.crs != CRS.from_user_input(out_crs):
                reference_shp = reference_shp.to_crs(
                    out_crs
                )  # TODO: make sure that the exposure_geoms file is projected in the out_crs (this doesn't happen now)

            # Spatially join the data
            modified_objects_gdf = gpd.sjoin(
                exposure_geoms,
                reference_shp[[attr_ref, "geometry"]],
                how="left",
            )

            # Sort and add the elevation to the shp values, append to the exposure dataframe
            # To be able to append the values from the GeoDataFrame to the DataFrame, it
            # must be sorted on the Object ID.
            identifier = (
                "Object ID"
                if "Object ID" in modified_objects_gdf.columns
                else "object_id"
            )

            # Group by the identifier and take the maximum value of the attribute reference
            # to avoid duplicates in the case of overlapping polygons in the data used
            # as reference.
            modified_objects_gdf = (
                modified_objects_gdf.groupby(identifier)
                .max(attr_ref)
                .sort_values(by=[identifier])
            )

        elif height_reference == "table":
            # Add table
            reference_table = pd.read_csv(path_ref)  # Vector
            # Join the data based on "Object ID"
            modified_objects_gdf = pd.merge(
                exposure_geoms,
                reference_table[["Object ID", attr_ref]],
                on="Object ID",
                how="left",
            )
            modified_objects_gdf = modified_objects_gdf.sort_values(
                by=["Object ID"]
            ).set_index("Object ID", drop=False)

        exposure_to_modify = exposure_to_modify.sort_values(by=["Object ID"]).set_index(
            "Object ID", drop=False
        )

        # Find indices of properties that are below the required level
        properties_below_level = (
            exposure_to_modify.loc[:, "Ground Floor Height"]
            + exposure_to_modify.loc[:, "Ground Elevation"]
            < modified_objects_gdf.loc[:, attr_ref] + raise_by
        )
        properties_no_reference_level = modified_objects_gdf[attr_ref].isna()
        to_change = properties_below_level & ~properties_no_reference_level

        self.logger.info(
            f"{properties_no_reference_level.sum()} properties have no "
            "reference height level. These properties are not raised."
        )

        original_df = exposure_to_modify.copy()  # to be used for metrics
        exposure_to_modify.loc[to_change, "Ground Floor Height"] = list(
            modified_objects_gdf.loc[to_change, attr_ref]
            + raise_by
            - exposure_to_modify.loc[to_change, "Ground Elevation"]
        )

        # Get some metrics on changes
        no_builds_to_change = sum(to_change)
        avg_raise = np.average(
            exposure_to_modify.loc[to_change, "Ground Floor Height"]
            - original_df.loc[to_change, "Ground Floor Height"]
        )
        self.logger.info(
            f"Raised {no_builds_to_change} properties with an average of {avg_raise}."
        )

        return exposure_to_modify.reset_index(drop=True)

    @staticmethod
    def _set_values_from_other_column(
        df: Union[pd.DataFrame, gpd.GeoDataFrame], col_to_set: str, col_to_copy: str
    ) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
        """Sets the values of <col_to_set> to where the values of <col_to_copy> are
        nan and deletes <col_to_copy>.
        """
        df.loc[df[col_to_copy].notna(), col_to_set] = df.loc[
            df[col_to_copy].notna(), col_to_copy
        ]
        del df[col_to_copy]
        return df
