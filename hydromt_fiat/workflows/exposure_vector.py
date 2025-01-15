import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Union
from shapely.geometry import Polygon, MultiPolygon
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

import pycountry_convert as pc
import geopandas as gpd
import numpy as np
import pandas as pd
from hydromt.data_catalog import DataCatalog
from pyproj import CRS

from hydromt_fiat.data_apis.national_structure_inventory import get_assets_from_nsi
from hydromt_fiat.api.data_types import Units, Conversion, Currency
from hydromt_fiat.data_apis.open_street_maps import (
    get_assets_from_osm,
    get_landuse_from_osm,
    get_buildings_from_osm,
    get_amenity_from_osm,
    get_roads_from_osm,
)

from hydromt_fiat.workflows.damage_values import (
    preprocess_jrc_damage_values,
    preprocess_hazus_damage_values,
    preprocess_damage_values,
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
    _REQUIRED_COLUMNS = ["object_id", "extract_method", "ground_flht"]
    _REQUIRED_VARIABLE_COLUMNS = ["fn_damage_{}", "max_damage_{}"]
    _OPTIONAL_COLUMNS = [
        "object_name",
        "primary_object_type",
        "secondary_object_type",
        "ground_elevtn",
    ]
    _OPTIONAL_VARIABLE_COLUMNS = ["Aggregation Label: {}", "Aggregation Variable: {}"]

    _CSV_COLUMN_DATATYPES = {
        "object_id": int,
        "object_name": str,
        "primary_object_type": str,
        "secondary_object_type": str,
        "extract_method": str,
        "Aggregation Label": str,
        "fn_damage_structure": str,
        "fn_damage_content": str,
        "Ground Flood Height": float,
        "ground_elevtn": float,
        "max_damage_structure": float,
        "max_damage_content": float,
    }

    def __init__(
        self,
        data_catalog: DataCatalog = None,
        logger: logging.Logger = None,
        region: gpd.GeoDataFrame = None,
        crs: str = None,
        unit: Units = Units.feet.value,
        damage_unit=Currency.dollar.value,
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
        unit : Units, optional
            The unit of the model, by default feet
        damage_unit : str, optional
            The unit/currency of the (potential) damages, by default USD$
        """
        super().__init__(
            data_catalog=data_catalog, logger=logger, region=region, crs=crs
        )
        self.exposure_db = pd.DataFrame()
        self.exposure_geoms = list()  # A list of GeoDataFrames
        self.unit = unit
        self._geom_names = list()  # A list of (original) names of the geometry (files)
        self.damage_unit = damage_unit
        self.building_footprints = gpd.GeoDataFrame

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
        gfh_unit: Units = None,
        ground_elevation: Union[int, float, str, Path, None] = None,
        grnd_elev_unit: Units = None,
        eur_to_us_dollar: bool = False,
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
            The extract_method to be used for all of the assets.
        extraction_method : str
            The extract_method to be used for all of the assets.
        eur_to_us_dollar: bool
            Convert JRC Damage Values (Euro 2010) into US-Dollars (2025)
        """
        if str(source).upper() == "NSI":
            # The NSI data is selected, so get the assets from the NSI
            self.logger.info(
                "Downloading assets from the National Structure Inventory."
            )
            polygon = self.region["geometry"].iloc[0]
            source_data = get_assets_from_nsi(self.data_catalog["NSI"].path, polygon)
        elif str(source).upper() == "OSM":
            # The OSM data is selected, so get the assets from  OSM
            self.logger.info("Downloading assets from Open Street Map.")
            source_data = self.data_catalog.get_geodataframe(
                source,
                geom=self.region.to_crs(4326),
            )
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

        # Check if the 'object_id' column is unique
        if len(self.exposure_db.index) != len(set(self.exposure_db["object_id"])):
            self.exposure_db["object_id"] = range(1, len(self.exposure_db.index) + 1)

        # Set the ground_flht if not yet set
        if ground_floor_height != source:
            self.setup_ground_floor_height(ground_floor_height)

        # Set the extract_method
        self.setup_extraction_method(extraction_method)

        # Set the exposure_geoms
        self.set_exposure_geoms(
            gpd.GeoDataFrame(self.exposure_db[["object_id", "geometry"]], crs=self.crs)
        )

        # Set the name to the geom_names
        self.set_geom_names("buildings")

        # Set the ground_flht if not yet set
        # TODO: Check a better way to access to to the geometries, self.empousure_geoms is a list an not a geodataframe
        if ground_elevation is not None:
            self.setup_ground_elevation(ground_elevation, grnd_elev_unit)

        # Remove the geometry column from the exposure_db
        if "geometry" in self.exposure_db:
            del self.exposure_db["geometry"]

    def setup_roads(
        self,
        source: Union[str, Path],
        road_damage: Union[str, Path, int, float],
        road_types: Union[str, List[str], bool] = True,
    ):
        self.logger.info("Setting up roads...")
        region = self.region.copy()
        if str(source).upper() == "OSM":
            region = region.to_crs(4326)
            polygon = region["geometry"].values[0]  # TODO check if this works each time
            roads = get_roads_from_osm(polygon, road_types)

            if roads.empty:
                self.logger.warning(
                    "No roads found in the selected region from source " f"{source}."
                )

            # Rename the columns to FIAT names
            roads.rename(
                columns={"highway": "secondary_object_type", "name": "object_name"},
                inplace=True,
            )

            # Add an object_id
            roads["object_id"] = range(1, len(roads.index) + 1)
        else:
            roads = self.data_catalog.get_geodataframe(source, geom=region)
            # add the function to segmentize the roads into certain segments

        # Add the primary_object_type and damage function, which is currently not set up to be flexible
        roads["primary_object_type"] = "road"
        roads["extract_method"] = "centroid"
        roads["ground_flht"] = 0

        self.logger.info(
            "The damage function 'road' is selected for all of the structure damage to the roads."
        )
        # Clip road to model boundaries
        roads = roads.clip(region)

        # Convert OSM road from meters to feet (if model unit is feet)
        road_length = get_road_lengths(roads)
        if self.unit == Units.feet.value and str(source).upper() == "OSM":
            road_length = road_length * Conversion.meters_to_feet.value
        road_length = road_length.apply(lambda x: f"{x:.2f}")

        # Add the max potential damage and the length of the segments to the roads
        if isinstance(road_damage, str):
            road_damage = self.data_catalog.get_dataframe(road_damage)
            roads[
                [
                    "max_damage_structure",
                    "segment_length",
                ]
            ] = get_max_potential_damage_roads(roads, road_damage)
        elif isinstance(road_damage, (int, float)) or road_damage is None:
            roads["segment_length"] = road_length
            roads["max_damage_structure"] = road_damage

        # Convert crs to exposure buildings crs
        if len(self.exposure_geoms) > 0:
            if roads.crs != self.exposure_geoms[0].crs:
                crs = self.exposure_geoms[0].crs
                roads = roads.to_crs(crs)

        # recreate object_id for buildings and roads
        full_exposure = pd.concat(
            [self.get_full_gdf(self.exposure_db), roads]
        ).reset_index(drop=True)
        full_exposure["object_id"] = full_exposure["object_id"].index
        roads = full_exposure[
            full_exposure["primary_object_type"].str.contains(
                "road", regex=False, na=False
            )
        ]
        buildings = full_exposure[
            ~full_exposure["primary_object_type"].str.contains(
                "road", regex=False, na=False
            )
        ]

        # Set the exposure_geoms
        self.set_exposure_geoms(roads[["object_id", "geometry"]])
        self.set_geom_names("roads")
        idx_buildings = self.geom_names.index("buildings")
        self.exposure_geoms[idx_buildings] = buildings[["object_id", "geometry"]]
        del full_exposure["geometry"]

        assert not full_exposure["object_id"].duplicated().any()

        # Update the exposure_db
        self.exposure_db = full_exposure

    def setup_buildings_from_multiple_sources(
        self,
        asset_locations: str,
        occupancy_source: Union[str, Path],
        max_potential_damage: Union[str, Path],
        ground_floor_height: Union[int, float, str, Path, None],
        extraction_method: str,
        occupancy_attr: Union[str, None] = None,
        damage_types: Union[List[str], None] = None,
        country: Union[str, None] = None,
        gfh_attribute_name: Union[str, List[str], None] = None,
        gfh_method: Union[str, List[str], None] = "nearest",
        gfh_unit: Units = None,
        max_dist: Union[int, float, List[float], List[int], None] = 10,
        ground_elevation: Union[int, float, str, Path, None] = None,
        grnd_elev_unit: Units = None,
        bf_conversion: bool = False,
        keep_unclassified: bool = True,
        damage_translation_fn: Union[Path, str] = None,
        eur_to_us_dollar: bool = False,
    ):
        """
        Set up the exposure data using multiple sources.

        Parameters
        ----------
        asset_locations : str
            The name of the vector dataset in the HydroMT Data Catalog or path to the
            vector dataset to be used to set up the asset locations. This can be
            either a point or polygon dataset.
        occupancy_source : str, Path
            The name of the vector dataset in the HydroMT Data Catalog or path to the
            vector dataset to be used to set up the occupancy types.
        max_potential_damage : str, Path
            The name of the vector dataset in the HydroMT Data Catalog or path to the
            vector dataset to be used to set up the maximum potential damage.
        ground_floor_height : int, float, str, Path, None
            Either a number (int or float) to give all assets the same ground floor
            height, a path to the data that can be used to add the ground floor
            height to the assets or None to use the data from 'asset_locations'.
        extraction_method : str
            The extract_method to be used for all of the assets.
        occupancy_attr : str, None
            The attribute name to be used to set the occupancy type. If None, the
            attribute name will be set to 'occupancy_type'.
        damage_types : List[str], None
            The list of damage types to be used. If None, the default damage types
            will be used.
        country : str, None
            The country to be used to set the damage function. If None, the default
            damage function will be used.
        gfh_attribute_name : str, List[str], None
            The attribute name to be used to set the ground_flht. If None, the
            attribute name will be set to 'ground_floor_height'.
        gfh_method : str, List[str], None
            The method to be used to add the ground_flht to the assets. If
            None, the default method will be used.
        max_dist : int, float, List[float], List[int], None
            The maximum distance to be used when adding the ground_flht to
            the assets. If None, the default maximum distance will be used.
        ground_elevation_file : int, float, str, Path, None
            The path to the ground_elevtn data. If None, the ground_elevtn will
            be set to 0.
        ground_elevation_unit : str
            The unit of the ground_elevtn data. If None, the unit will be set to
            'm'.
        bf_conversion : bool
            A flag to indicate if the building footprints should be converted into
            centroids. If True, the building footprints will be converted into
            centroids.
        keep_unclassified : bool
            A flag to indicate if the unclassified values should be kept. If True, the
            unclassified values will be kept.
        damage_translation_fn : Path, str
            The path to the file that contains the translation of the damage types to
            the damage values. If None, the default translation file will be used.
        eur_to_us_dollar: bool
            Convert JRC Damage Values (Euro 2010) into US-Dollars (2025)

        Returns
        -------
        None
        """
        self.logger.info("Setting up exposure data from multiple sources...")

        # If asset location_fn != OSM and equals occupancy type, take the geometry from occupancy type
        self.setup_asset_locations(asset_locations)
        self.setup_occupancy_type(
            occupancy_source, occupancy_attr, keep_unclassified=keep_unclassified
        )
        self.setup_max_potential_damage(
            max_potential_damage,
            damage_types,
            country=country,
            damage_translation_fn=damage_translation_fn,
            eur_to_us_dollar=eur_to_us_dollar,
        )
        if (
            any(
                isinstance(geom, Polygon) for geom in self.exposure_geoms[0]["geometry"]
            )
            or any(
                isinstance(geom, MultiPolygon)
                for geom in self.exposure_geoms[0]["geometry"]
            )
            and bf_conversion
        ):
            self.building_footprints = self.exposure_geoms[0]
            self.convert_bf_into_centroids(
                self.exposure_geoms[0], self.exposure_geoms[0].crs
            )
        self.setup_ground_floor_height(
            ground_floor_height, gfh_attribute_name, gfh_method, max_dist, gfh_unit
        )
        self.setup_extraction_method(extraction_method)
        self.setup_ground_elevation(ground_elevation, grnd_elev_unit)

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
        # if isinstance(asset_locations, str):
        if str(asset_locations).upper() == "OSM":
            polygon = self.region.to_crs(4326).geometry.values[0]
            assets = get_assets_from_osm(polygon)

            if assets.empty:
                self.logger.warning(
                    "No assets found in the selected region from source "
                    f"{asset_locations}."
                )

            # Rename the osmid column to object_id
            assets.rename(columns={"osmid": "object_id"}, inplace=True)
        else:
            assets = self.data_catalog.get_geodataframe(
                asset_locations, geom=self.region
            )

        # Set the CRS of the exposure data
        self.crs = get_crs_str_from_gdf(assets.crs)

        # Check if the 'object_id' column exists and if so, is unique
        if "object_id" not in assets.columns:
            assets["object_id"] = range(1, len(assets.index) + 1)
        else:
            if len(assets.index) != len(set(assets["object_id"])):
                assets["object_id"] = range(1, len(assets.index) + 1)

        # Set the asset locations to the geometry variable (self.exposure_geoms)
        # and set the geom name
        if len(assets.columns) > 2:
            assets = assets[["object_id", "geometry"]]

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
        type_add: str = "primary_object_type",
        keep_unclassified: bool = True,
    ) -> None:
        """Set up the Primary and secondary_object_type.
        Parameters
        ----------
        occupancy_source : str
            The occupancy source (default: Open Street Map or National Structure Inventory )
        occupancy_attr : str
            Other classification to be updated by Primary/Secondary Classification
        type_add : str
            "primary_object_type" or "secondary_object_type"
        keep_unclassified : Bool
            Whether to re-classify Primary/secondary_object_types as "residential" or remove rows if no Object Type
        """
        self.logger.info(f"Setting up occupancy type from {str(occupancy_source)}...")
        if str(occupancy_source).upper() == "OSM":
            occupancy_type = self.setup_occupancy_type_from_osm()
            occupancy_landuse = occupancy_type[0]
            occupancy_building = occupancy_type[1]
            occupancy_amenity = occupancy_type[2]

            occupancy_types = ["primary_object_type", "secondary_object_type"]
        else:
            occupancy_building = self.data_catalog.get_geodataframe(
                occupancy_source, geom=self.region
            )
            if occupancy_attr is not None:
                occupancy_building.rename(
                    columns={occupancy_attr: type_add}, inplace=True
                )
            occupancy_types = [type_add]

        # Check if the CRS of the occupancy map is the same as the exposure data
        if occupancy_building.crs != self.crs:
            occupancy_building = occupancy_building.to_crs(self.crs)
            occupancy_landuse = occupancy_landuse.to_crs(self.crs)
            occupancy_amenity = occupancy_amenity.to_crs(self.crs)

            self.logger.warning(
                "The CRS of the occupancy map is not the same as that "
                "of the exposure data. The occupancy map has been "
                f"reprojected to the CRS of the exposure data ({self.crs}) before "
                "doing the spatial join."
            )

        to_keep = ["geometry"] + occupancy_types

        # Spatially join the exposure data with the occupancy buildings
        if len(self.exposure_geoms) == 1:
            # If there is only one exposure geom, do the spatial join with the
            # occupancy_landuse. Only take the largest overlapping object from the
            # occupancy_landuse.
            gdf = gpd.sjoin(
                self.exposure_geoms[0],
                occupancy_building[to_keep],
                how="left",
                predicate="intersects",
            )
            gdf.drop(columns=["index_right"], inplace=True)

            if occupancy_source == "OSM":

                ## Landuse
                # Replace values with landuse if applicable for Primary and Secondary Object Type
                occupancy_landuse.rename(
                    columns={
                        "primary_object_type": "pot",
                        "secondary_object_type": "pot_2",
                    },
                    inplace=True,
                )

                gdf_landuse = gdf.sjoin(
                    occupancy_landuse[["geometry", "pot", "pot_2"]],
                    how="left",
                    predicate="intersects",
                )
                gdf_landuse.reset_index(inplace=True, drop=True)

                # Replace values with landuse
                gdf_landuse.loc[gdf_landuse["pot"].notna(), "primary_object_type"] = (
                    gdf_landuse.loc[gdf_landuse["pot"].notna(), "pot"]
                )
                gdf_landuse.loc[gdf_landuse["pot"].notna(), "secondary_object_type"] = (
                    gdf_landuse.loc[gdf_landuse["pot"].notna(), "pot_2"]
                )
                gdf_landuse.drop(columns=["index_right", "pot", "pot_2"], inplace=True)

                ## Amenity
                # Fill nan values with values amenity for Primary and Secondary Object Type
                occupancy_amenity.rename(
                    columns={
                        "primary_object_type": "pot",
                        "secondary_object_type": "pot_2",
                    },
                    inplace=True,
                )

                gdf_amenity = gdf_landuse.sjoin(
                    occupancy_amenity[["geometry", "pot", "pot_2"]],
                    how="left",
                    predicate="intersects",
                )
                gdf_amenity.reset_index(inplace=True, drop=True)
                # Replace values with amenity
                gdf_amenity.loc[gdf_amenity["pot"].notna(), "primary_object_type"] = (
                    gdf_amenity["pot"]
                )
                gdf_amenity.loc[
                    gdf_amenity["pot_2"].notna(), "secondary_object_type"
                ] = gdf_amenity["pot_2"]

                gdf_amenity.drop(columns=["index_right", "pot", "pot_2"], inplace=True)

                # Rename some major catgegories
                gdf_amenity.loc[
                    gdf_amenity["secondary_object_type"] == "yes",
                    "secondary_object_type",
                ] = "residential"
                gdf_amenity.loc[
                    gdf_amenity["secondary_object_type"] == "house",
                    "secondary_object_type",
                ] = "residential"
                gdf_amenity.loc[
                    gdf_amenity["secondary_object_type"] == "apartments",
                    "secondary_object_type",
                ] = "residential"
                gdf = gdf_amenity
                gdf.drop_duplicates(subset="geometry", inplace=True)

            # Remove the objects that do not have a primary_object_type, that were not
            # overlapping with the land use map, or that had a land use type of 'nan'.
            if "primary_object_type" in gdf.columns:
                gdf.loc[gdf["primary_object_type"] == "", "primary_object_type"] = (
                    np.nan
                )
                nr_without_primary_object = len(
                    gdf.loc[gdf["primary_object_type"].isna()].index
                )
                if keep_unclassified:
                    # merge assets with occupancy
                    if len(self.exposure_geoms[0]) > len(gdf):
                        gdf = pd.concat(
                            [gdf, self.exposure_geoms[0]], ignore_index=True
                        )
                        gdf.drop_duplicates(subset="object_id", inplace=True)
                    # assign residential if no primary object type
                    gdf.loc[
                        gdf["primary_object_type"].isna(), "secondary_object_type"
                    ] = "residential"
                    gdf.loc[
                        gdf["primary_object_type"].isna(), "primary_object_type"
                    ] = "residential"
                    self.logger.warning(
                        f"{nr_without_primary_object} objects were not overlapping with the "
                        "land use data and will be classified as residential buildings."
                    )
                else:
                    self.logger.warning(
                        f"{nr_without_primary_object} objects do not have a Primary Object "
                        "Type and will be removed from the exposure data."
                    )
                gdf = gdf.loc[gdf["primary_object_type"] != ""]

                nr_without_landuse = len(
                    gdf.loc[gdf["primary_object_type"].isna()].index
                )
                if nr_without_landuse > 0:
                    self.logger.warning(
                        f"{nr_without_landuse} objects were not overlapping with the "
                        "land use data and will be removed from the exposure data."
                    )
                    gdf = gdf[gdf["primary_object_type"].notna()]
                    gdf = gdf[gdf["primary_object_type"] != ""]

            # Remove object_id duplicates
            gdf.drop_duplicates(inplace=True, subset="object_id")
            gdf.reset_index(drop=True, inplace=True)

            # Add secondary Object Type if not in columns
            if "secondary_object_type" not in gdf.columns:
                gdf["secondary_object_type"] = gdf["primary_object_type"]

            # Update the exposure geoms
            self.exposure_geoms[0] = gdf[["object_id", "geometry"]]

            # Remove the geometry column from the exposure database
            del gdf["geometry"]

            # Update the exposure database
            if type_add in self.exposure_db:
                if "primary_object_type" in gdf.columns:
                    gdf.rename(columns={"primary_object_type": "pot"}, inplace=True)
                    self.exposure_db = pd.merge(
                        self.exposure_db, gdf, on="object_id", how="left"
                    )
                    self.exposure_db = self._set_values_from_other_column(
                        self.exposure_db, "primary_object_type", "pot"
                    )
                    # Replace secondary_object_type with new classification to assign correct damage curves
                    self.exposure_db = pd.merge(
                        self.exposure_db, gdf, on="object_id", how="left"
                    )
                    self.exposure_db = self._set_values_from_other_column(
                        self.exposure_db, "secondary_object_type", "pot"
                    )
                elif "secondary_object_type" in gdf.columns:
                    gdf.rename(columns={"secondary_object_type": "pot"}, inplace=True)
                    self.exposure_db = pd.merge(
                        self.exposure_db, gdf, on="object_id", how="left"
                    )
                    self.exposure_db = self._set_values_from_other_column(
                        self.exposure_db, "secondary_object_type", "pot"
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
        occupancy_attributes = ["landuse", "building", "amenity"]
        # Get the land use from OSM
        polygon = self.region.to_crs(4326).geometry[0]
        occupancy_landuse = get_landuse_from_osm(polygon)
        occupancy_buildings = get_buildings_from_osm(polygon)
        occupancy_amenity = get_amenity_from_osm(polygon)
        occupancy_types = [occupancy_landuse, occupancy_buildings, occupancy_amenity]

        for occupancy, occupancy_attribute in zip(
            occupancy_types, occupancy_attributes
        ):
            if occupancy.empty:
                self.logger.warning(
                    f"No {occupancy_attribute } data found in the selected region from source 'OSM'."
                )

            # Log the unique occupancy types
            self.logger.info(
                f"The following unique {occupancy_attribute} are found in the OSM data: "
                f"{list(occupancy[occupancy_attribute].unique())}"
            )

            # Map the landuse/buildings/amenity types to types used in the JRC global vulnerability curves
        # and the JRC global damage values
        jrc_osm_mapping = self.data_catalog.get_dataframe("jrc_osm_mapping")

        # landuse
        landuse_to_jrc_mapping = jrc_osm_mapping[["osm_key_landuse", "jrc_key_landuse"]]
        landuse_to_jrc_mapping = dict(
            zip(
                landuse_to_jrc_mapping["osm_key_landuse"],
                landuse_to_jrc_mapping["jrc_key_landuse"],
            )
        )
        # buildings
        buildings_to_jrc_mapping = jrc_osm_mapping[
            ["osm_key_building", "jrc_key_building"]
        ]
        buildings_to_jrc_mapping = dict(
            zip(
                buildings_to_jrc_mapping["osm_key_building"],
                buildings_to_jrc_mapping["jrc_key_building"],
            )
        )
        # amenity
        amenity_to_jrc_mapping = jrc_osm_mapping[["osm_key_amenity", "jrc_key_amenity"]]
        amenity_to_jrc_mapping = dict(
            zip(
                amenity_to_jrc_mapping["osm_key_amenity"],
                amenity_to_jrc_mapping["jrc_key_amenity"],
            )
        )

        jrc_mapping_type = [
            landuse_to_jrc_mapping,
            buildings_to_jrc_mapping,
            amenity_to_jrc_mapping,
        ]

        # Create primary_object_type column for OSM data
        for occupancy, occupancy_attribute, jrc_mapping in zip(
            occupancy_types, occupancy_attributes, jrc_mapping_type
        ):
            occupancy["primary_object_type"] = occupancy[occupancy_attribute].map(
                jrc_mapping
            )
            occupancy.rename(
                columns={occupancy_attribute: "secondary_object_type"}, inplace=True
            )
        # In next step where spatial joint of exposure and occupancy map do a spatial joint with buildings, where are Nan values.

        return occupancy_types

    def setup_extraction_method(self, extraction_method: str) -> None:
        self.exposure_db["extract_method"] = extraction_method

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
        gfh_attribute_name: Union[str, List[str], None] = None,
        gfh_method: Union[str, List[str], None] = "nearest",
        max_dist: float = 10,
        gfh_unit: Units = None,
    ) -> None:
        """Set the ground_flht of the exposure data. This function overwrites
        the existing ground_flht column if it already exists.

        Parameters
        ----------
        ground_floor_height : Union[int, float, None, str, Path, List[str], List[Path]]
            A number to set the ground_flht of all assets to the same value, a
            path to a file that contains the ground_flht of each asset, or a
            list of paths to files that contain the ground_flht of each asset,
            in the order of preference (the first item in the list gets the highest
            priority in assigning the values).
        gfh_attribute_name : Union[str, List[str]], optional
            The name of the attribute that contains the ground_flht in the
            file(s) that are submitted. If multiple `ground_floor_height` files are
            submitted, the attribute names are linked to the files in the same order as
            the files are submitted. By default None.
        gfh_method : Union[str, List[str]], optional
            The method to use to assign the ground_flht to the assets. If
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
                # If the ground_flht is input as a number, assign all objects with
                # the same ground_flht.
                self.exposure_db["ground_flht"] = ground_floor_height
            elif isinstance(ground_floor_height, str) or isinstance(
                ground_floor_height, Path
            ):
                # A single file is used to assign the ground_flht to the assets
                gfh = self.data_catalog.get_geodataframe(ground_floor_height)

                # If method is "intersection" remove columns from gfh exept for attribute name and geometry
                if gfh_method == "intersection":
                    columns_to_drop = [
                        col
                        for col in gfh.columns
                        if col != gfh_attribute_name and col != "geometry"
                    ]
                    gfh = gfh.drop(columns=columns_to_drop)

                gdf = self.get_full_gdf(self.exposure_db)

                # If roads in model filter out for spatial joint
                if gdf["primary_object_type"].str.contains("road").any():
                    gdf_roads = gdf[gdf["primary_object_type"].str.contains("road")]
                    gdf = join_spatial_data(
                        gdf[~gdf.isin(gdf_roads)].dropna(subset=["geometry"]),
                        gfh,
                        gfh_attribute_name,
                        gfh_method,
                        max_dist,
                        self.logger,
                    )
                    gdf = pd.concat([gdf, gdf_roads])
                else:
                    gdf = join_spatial_data(
                        gdf, gfh, gfh_attribute_name, gfh_method, max_dist, self.logger
                    )

                # If method is "intersection" rename *"_left" to original exposure_db name
                if gfh_method == "intersection":
                    self.intersection_method(gdf)

                # Update exposure_db
                self.exposure_db = self._set_values_from_other_column(
                    gdf, "ground_flht", gfh_attribute_name
                )

                # Unit conversion
                if gfh_unit:
                    self.unit_conversion("Ground Floor Height", gfh_unit)

                if "geometry" in self.exposure_db.columns:
                    self.exposure_db.drop(columns=["geometry"], inplace=True)

            elif isinstance(ground_floor_height, list):
                # Multiple files are used to assign the ground_flht to the assets
                NotImplemented
        else:
            # Set the ground_flht to 0 if the user did not specify any
            # ground_flht.
            self.exposure_db["ground_flht"] = 0

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
        damage_translation_fn: Union[str, Path] = None,
        eur_to_us_dollar: bool = False,
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
        damage_translation_fn: Union[Path, str], optional
            The path to the translation function that can be used to relate user damage curves with user damages.
        eur_to_us_dollar: bool
            Convert JRC Damage Values (Euro 2010) into US-Dollars (2025)
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
                self.exposure_db[f"max_damage_{damage_type}"] = max_potential_damage

        elif isinstance(max_potential_damage, list):
            # Multiple files are used to assign the ground_flht to the assets
            for max_damage, attribute, method, max_dis, damage_type in zip(
                max_potential_damage,
                attribute_name,
                method_damages,
                max_dist,
                damage_types,
            ):
                # When the max_potential_damage is a string but not jrc_damage_values
                # or hazus_max_potential_damages. Here, a single file is used to
                # assign the ground_flht to the assets
                mpd = self.data_catalog.get_geodataframe(max_damage)

                # If method is "intersection" remove columns from gfh exept for attribute name and geometry
                if method == "intersection":
                    columns_to_drop = [
                        col
                        for col in mpd.columns
                        if col != attribute and col != "geometry"
                    ]
                    mpd = mpd.drop(columns=columns_to_drop)

                # Get exposure data
                gdf = self.get_full_gdf(self.exposure_db)

                # If roads in model filter out for spatial joint
                if gdf["primary_object_type"].str.contains("road").any():
                    gdf_roads = gdf[gdf["primary_object_type"].str.contains("road")]
                    gdf = join_spatial_data(
                        gdf[~gdf.isin(gdf_roads)].dropna(subset=["geometry"]),
                        mpd,
                        attribute,
                        method,
                        max_dis,
                        self.logger,
                    )
                    gdf = pd.concat([gdf, gdf_roads])
                else:
                    gdf = join_spatial_data(
                        gdf,
                        mpd,
                        attribute,
                        method,
                        max_dis,
                        self.logger,
                    )

                # If method is "intersection" rename *"_left" to original exposure_db name
                if method == "intersection":
                    self.intersection_method(gdf)

                # Update exposure_db with updated dataframe
                self.exposure_db = self._set_values_from_other_column(
                    gdf,
                    f"max_damage_{damage_type}",
                    attribute,
                )
                if "geometry" in self.exposure_db.columns:
                    self.exposure_db.drop(columns=["geometry"], inplace=True)

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

                damage_values = preprocess_jrc_damage_values(
                    damage_source, country, eur_to_us_dollar
                )

            elif max_potential_damage == "hazus_max_potential_damages":
                damage_source = self.data_catalog.get_dataframe(max_potential_damage)
                damage_values = preprocess_hazus_damage_values(damage_source)

            # Calculate the area of each object
            gdf = self.get_full_gdf(self.exposure_db)[
                ["primary_object_type", "geometry"]
            ]
            gdf = get_area(gdf)
            gdf = gdf.dropna(subset="primary_object_type")

            # Set the damage values to the exposure data
            self.set_max_potential_damage_columns(
                damage_types, damage_values, gdf, max_potential_damage
            )

        elif isinstance(max_potential_damage, str) or isinstance(
            max_potential_damage, Path
        ):
            if isinstance(max_potential_damage, Path):
                max_potential_damage = str(max_potential_damage)

            # Using a csv file with a translation table to assign damages to damage curves
            if max_potential_damage.endswith(".csv") or max_potential_damage.endswith(
                ".xlsx"
            ):
                damage_source = self.data_catalog.get_dataframe(max_potential_damage)
                damage_values = preprocess_damage_values(
                    damage_source, damage_translation_fn
                )

                # Calculate the area of each object
                gdf = self.get_full_gdf(self.exposure_db)[
                    ["primary_object_type", "geometry"]
                ]
                gdf = get_area(gdf)
                gdf = gdf.dropna(subset="primary_object_type")

                # Set the damage values to the exposure data
                self.set_max_potential_damage_columns(
                    damage_types, damage_values, gdf, max_potential_damage
                )
            else:
                # When the max_potential_damage is a string but not jrc_damage_values
                # or hazus_max_potential_damages. Here, a single file is used to
                # assign the mpd to the assets
                mpd = self.data_catalog.get_geodataframe(max_potential_damage)
                gdf = self.get_full_gdf(self.exposure_db)

                # If roads in model filter out for spatial joint
                if gdf["primary_object_type"].str.contains("road").any():
                    gdf_roads = gdf[gdf["primary_object_type"].str.contains("road")]
                    # Spatial joint exposure and updated damages
                    gdf = join_spatial_data(
                        gdf[~gdf.isin(gdf_roads)].dropna(subset=["geometry"]),
                        mpd,
                        attribute_name,
                        method_damages,
                        max_dist,
                        self.logger,
                    )
                    gdf = pd.concat([gdf, gdf_roads])
                else:
                    gdf = join_spatial_data(
                        gdf, mpd, attribute_name, method_damages, max_dist, self.logger
                    )
                self.exposure_db = self._set_values_from_other_column(
                    gdf,
                    f"max_damage_{damage_types[0]}",
                    attribute_name,
                )

    def setup_ground_elevation(
        self, ground_elevation: Union[None, str, Path], grnd_elev_unit: Units = None
    ) -> None:
        """
        Set the ground elevation of the exposure data.

        Parameters
        ----------
        ground_elevation : Union[int, float, None, str, Path]
            Either a number (int or float) to give all assets the same ground elevation
            or a path to the data that can be used to add the ground elevation to the assets.
        unit : str
            The unit of the ground elevation. This can be either 'meters' or 'feet'.
        """

        if ground_elevation:
            self.exposure_db["ground_elevtn"] = ground_elevation_from_dem(
                ground_elevation=ground_elevation,
                exposure_db=self.exposure_db,
                exposure_geoms=self.get_full_gdf(self.exposure_db),
            )

            # Unit conversion
            if grnd_elev_unit:
                self.unit_conversion(parameter="grnd_elevtn", unit=grnd_elev_unit)

        else:
            self.logger.warning(
                "ground_elevtn is not recognized by the setup_ground_elevation function"
            )
            self.logger.warning("ground_elevtn will be set to 0")
            self.exposure_db["ground_elevtn"] = 0

    def setup_impacted_population(
        self,
        impacted_population_fn: Union[
            int, float, str, Path, List[str], List[Path], pd.DataFrame
        ] = None,
        attribute_name: Union[str, List[str], None] = None,
        method_impacted_pop: Union[str, List[str], None] = "intersection",
        max_dist: float = 10,
    ) -> None:
        """Sets up the impacted population data for the exposure model.

        Parameters
        ----------
        impacted_population_fn : Union[int, float, str, Path, List[str], List[Path], pd.DataFrame], optional
            The source of the impacted population data. It can be a path to a file, a list of paths,
            a DataFrame, or a direct value.
        attribute_name : Union[str, List[str], None], optional
            The attribute name(s) to be used for identifying impacted population data, by default None.
        method_impacted_pop : Union[str, List[str], None], optional
            The method to be used for processing impacted population data, by default "intersection".
        max_dist : float, optional
            The maximum allowable distance for spatial joins, by default 10.

        Notes
        -----
        This function updates the exposure database with impacted population data by performing spatial
        joins and setting the values from the specified attribute.
        """

        # TODO: Add support for other methods

        if isinstance(impacted_population_fn, str) or isinstance(
            impacted_population_fn, Path
        ):
            # When the max_potential_damage is a string but not jrc_damage_values
            # or hazus_max_potential_damages. Here, a single file is used to
            # assign the mpd to the assets
            pop_impacted = self.data_catalog.get_geodataframe(impacted_population_fn)
            gdf = self.get_full_gdf(self.exposure_db)

            # If roads in model filter out for spatial joint
            if gdf["primary_object_type"].str.contains("road").any():
                gdf_roads = gdf[gdf["primary_object_type"].str.contains("road")]
                # Spatial joint exposure and updated damages
                gdf = join_spatial_data(
                    gdf[~gdf.isin(gdf_roads)].dropna(subset=["geometry"]),
                    pop_impacted,
                    attribute_name,
                    method_impacted_pop,
                    max_dist,
                    self.logger,
                )
                gdf = pd.concat([gdf, gdf_roads])
            else:
                gdf = join_spatial_data(
                    gdf,
                    pop_impacted,
                    attribute_name,
                    method_impacted_pop,
                    max_dist,
                    self.logger,
                )

            del gdf["geometry"]
            self.exposure_db = self._set_values_from_other_column(
                gdf,
                "max_affected_people",
                attribute_name,
            )
            self.exposure_db["fn_affected_people"] = "population"

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
        if "object_id" not in updated_max_potential_damages.columns:
            self.logger.warning(
                "Trying to update the maximum potential damages but no 'object_id' column is found in the updated_max_potential_damages variable."
            )
            return

        damage_cols = [
            c for c in updated_max_potential_damages.columns if "max_damage_" in c
        ]
        updated_max_potential_damages.set_index("object_id", inplace=True)
        self.exposure_db.set_index("object_id", inplace=True, drop=False)

        self.exposure_db[damage_cols] = updated_max_potential_damages[damage_cols]
        self.exposure_db.reset_index(drop=True, inplace=True)

    def raise_ground_floor_height(
        self,
        raise_by: Union[int, float],
        objectids: List[int],
        height_reference: str = "",
        path_ref: str = None,
        attr_ref: str = "STATIC_BFE",
    ):
        """Raises the ground_flht of selected objects to a certain level.

        Parameters
        ----------
        raise_by : Union[int, float]
            The level to raise the selected objects by.
        objectids : List[int]
            A list of object_ids to select the exposure objects to raise the ground
            floor of.
        height_reference : str, optional
            Either 'datum' when the ground_flht should be raised relative to the
            Datum or 'geom' when the ground_flht should be raised relative to
            the attribute `attr_ref` in the geometry file `path_ref`, by default ""
        path_ref : str, optional
            The full path to the geometry file used to calculate the Ground Floor
            Height if the `height_reference` is set 'geom', by default None
        attr_ref : str, optional
            The attribute in the geometry file `path_ref`, by default "STATIC_BFE"
        """
        # ground_flht attr already exist, update relative to a reference file or datum
        # Check if the ground_flht column already exists
        if "ground_flht" not in self.exposure_db.columns:
            self.logger.warning(
                "Trying to update the ground_flht but the attribute does not "
                "yet exist in the exposure data."
            )
            return

        # Get the index of the objects to raise the ground_flht.
        idx = self.exposure_db.loc[self.exposure_db["object_id"].isin(objectids)].index

        # Log the number of objects that are being raised.
        self.logger.info(
            f"Raising the ground_flht of {len(idx)} properties to {raise_by}."
        )  # TODO: add the unit of the ground_flht

        if height_reference.lower() == "datum":
            # Elevate the object with 'raise_to'
            self.logger.info(
                "Raising the ground_flht of the properties relative to Datum."
            )
            self.exposure_db.loc[
                (
                    self.exposure_db["ground_flht"] + self.exposure_db["ground_elevtn"]
                    < raise_by
                )
                & self.exposure_db.index.isin(idx),
                "ground_flht",
            ] += raise_by - (
                self.exposure_db["ground_flht"] + self.exposure_db["ground_elevtn"]
            )

        elif height_reference.lower() in ["geom", "table"]:
            # Elevate the objects relative to the surface water elevation map that the
            # user submitted.
            self.logger.info(
                "Raising the ground_flht of the properties relative to "
                f"{Path(path_ref).name}, with column {attr_ref}."
            )

            if len(self.exposure_geoms) == 0:
                self.set_exposure_geoms_from_xy()

            # TODO the way that indexing and geom indexing is working now is error prone!!!!

            new_values = self.set_height_relative_to_reference(
                self.exposure_db.loc[idx, :],
                self.exposure_geoms[0].iloc[idx, :],
                height_reference,
                path_ref,
                attr_ref,
                raise_by,
                self.crs,
            ).set_index("object_id")
            self.exposure_db.set_index("object_id", inplace=True)
            self.exposure_db.loc[objectids, "ground_flht"] = new_values.loc[
                objectids, "ground_flht"
            ]
            self.exposure_db.reset_index(drop=False, inplace=True)
            self.logger.info(
                "set_height_relative_to_reference can for now only be used for the "
                "original exposure data."
            )

        else:
            self.logger.warning(
                "The height reference of the ground_flht is set to "
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
            A list of object_ids to select the exposure objects to truncate the damage
            functions of.
        floodproof_to : Union[int, float]
            The height to floodproof to, i.e. to truncate the damage functions to.
        damage_function_types : List[str]
            A list of damage types that should be considered for the new composite area,
            e.g. ['structure', 'content']. The function is case-sensitive.
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
        idx = self.exposure_db.loc[self.exposure_db["object_id"].isin(ids)].index

        # Find all damage functions that should be modified and truncate with
        # floodproof_to.
        for df_type in damage_function_types:
            dfs_to_modify = [
                d
                for d in list(
                    self.exposure_db.iloc[idx, :][f"fn_damage_{df_type}"].unique()
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
            if c.split("_")[-1] in damage_function_types
        ]
        self.exposure_db.iloc[idx, damage_function_column_idx] = (
            self.exposure_db.iloc[idx, damage_function_column_idx] + df_name_suffix
        )

    def convert_bf_into_centroids(self, gdf_bf, crs):
        """Convert building footprints into point data.

        Parameters
        ----------
        gdf_bf : gpd.GeoDataFrame
            Path(s) to the aggregation area(s).
        crs : str
            The CRS of the model.
        """
        list_centroid = []
        list_object_id = []
        for index, row in gdf_bf.iterrows():
            centroid = row["geometry"].centroid
            list_centroid.append(centroid)
            list_object_id.append(row["object_id"])
        data = {"object_id": list_object_id, "geometry": list_centroid}
        gdf_centroid = gpd.GeoDataFrame(data, columns=["object_id", "geometry"])
        gdf = gdf_bf.merge(gdf_centroid, on="object_id", suffixes=("_gdf1", "_gdf2"))
        gdf.drop(columns="geometry_gdf1", inplace=True)
        gdf.rename(columns={"geometry_gdf2": "geometry"}, inplace=True)
        gdf.drop_duplicates(inplace=True)
        gdf = gpd.GeoDataFrame(gdf, geometry=gdf["geometry"])

        # Update geoms
        self.exposure_geoms[0] = gdf
        self.exposure_geoms[0].crs = crs

    def calculate_damages_new_exposure_object(
        self, percent_growth: float, damage_types: List[str]
    ):
        damages_cols = [
            c
            for c in self.get_max_potential_damage_columns()
            if c.split("max_damage_")[-1] in damage_types
        ]
        new_damages = dict()

        # Calculate the Max. Potential Damages for the new area. This is the total
        # percentage of population growth multiplied with the total sum of the Max
        # Potential Structural/Content/Other Damage.
        for c in damages_cols:
            total_damages = sum(self.exposure_db[c].fillna(0))
            new_damages[c.split("max_damage_")[-1]] = total_damages * percent_growth

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
            e.g. ['structure', 'content']. The function is case-sensitive.
        vulnerability : Vulnerability
            The Vulnerability object from the FiatModel.
        elevation_reference : str
            Either 'datum' when the ground_flht should be set relative to the
            Datum or 'geom' when the ground_flht should be set relative to the
            attribute `attr_ref` in the geometry file `path_ref`.
        path_ref : str, optional
            The full path to the geometry file used to calculate the Ground Floor
            Height if the `elevation_reference` is set 'geom', by default None
        attr_ref : str, optional
            The attribute in the geometry file `path_ref`, by default None
        new_composite_area : bool
            Define whether new composite area to select correct aggregation zones functionality.
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
                for df in self.exposure_db["fn_damage_" + damage_type].unique()
                if df == df
            ]
            for damage_type in damage_types
        }
        df_value_counts_dict = {
            damage_type: self.exposure_db["fn_damage_" + damage_type].value_counts()
            for damage_type in damage_types
        }
        new_damage_functions = vulnerability.calculate_weighted_damage_function(
            df_dict, df_value_counts_dict
        )

        # Add the new development area as an object to the Exposure Modification file.
        new_area = gpd.read_file(geom_file, engine="pyogrio")
        # check_crs(new_area, geom_file)  #TODO implement again

        # Check if the column "height" is in the provided spatial file, which indicates the individual heights above the reference
        # If not the provided value will be used uniformly
        if "height" not in new_area.columns:
            new_area["height"] = ground_floor_height
            self.logger.info(
                f"Using uniform value of {ground_floor_height}"
                f"to specify the elevation above {elevation_reference} of FFE of new composite area(s)."
            )
        else:
            self.logger.info(
                f"Using 'height' column from {geom_file} to specify the elevation above {elevation_reference} "
                "for FFE of new composite area(s)."
            )

        new_area["object_id"] = None  # add object_id column to area file

        new_objects = []

        # Calculate the total area to use for adding the damages relative to area
        total_area = (
            new_area.geometry.area.sum()
        )  # TODO: reproject to a projected CRS if this is a geographic CRS?

        # There should be an attribute 'object_id' in the new development area shapefile.
        # This ID is used to join the shapefile to the exposure data.
        join_id_name = "object_id"
        if join_id_name not in new_area.columns:
            self.logger.debug(
                'The unique ID column in the New Development Area is not named "object_id", '
                'therefore, a new unique identifyer named "object_id" is added.'
            )
            new_area[join_id_name] = range(len(new_area.index))

        max_id = self.exposure_db["object_id"].max()
        new_geoms_ids = []
        for i in range(len(new_area.index)):
            new_geom = new_area.geometry.iloc[i]
            new_id = max_id + 1
            new_area["object_id"].iloc[i] = new_id  # assign object_id to polygons
            perc_damages = new_geom.area / total_area

            # Idea: Reduction factor for the part of the area is not build-up?

            dict_new_objects_data = {
                "object_id": [new_id],
                "object_name": ["New development area: " + str(new_id)],
                "primary_object_type": ["New development area"],
                "secondary_object_type": ["New development area"],
                "extract_method": ["area"],
                "ground_flht": [0],
                "ground_elevtn": [0],
            }
            dict_new_objects_data.update(
                {
                    f"fn_damage_{damage_type}": [new_damage_functions[damage_type]]
                    for damage_type in damage_types
                }
            )
            dict_new_objects_data.update(
                {
                    f"max_damage_{damage_type}": [
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

        # Create a new GeoDataFrame with the new geometries and the object_id
        _new_exposure_geoms = gpd.GeoDataFrame(
            data=new_geoms_ids, columns=["geometry", "object_id"], crs=self.crs
        )

        # If the user supplied ground_elevtn data, assign that to the new
        # composite areas
        if ground_elevation is not None:
            new_objects["ground_elevtn"] = ground_elevation_from_dem(
                ground_elevation=ground_elevation,
                exposure_db=new_objects,
                exposure_geoms=_new_exposure_geoms,
            )

        if elevation_reference == "datum":
            # Ensure that the new objects have a first floor height that elevates them above the requirement
            new_objects["ground_flht"] = new_objects.apply(
                lambda row: max(
                    row["ground_flht"],
                    new_area.loc[row.name, "height"] - row["ground_elevtn"],
                ),
                axis=1,
            )
            self.logger.info(
                f"The elevation of the new development area is {new_area['height'].values} {self.unit}"
                " relative to datum."  # TODO: make unit flexible
            )
        elif elevation_reference == "geom":
            self.logger.info(
                f"The elevation of the new development area is {new_area['height'].values} {self.unit}"
                f" relative to {Path(path_ref).stem}. The height of the floodmap is"
                f" identified with column {attr_ref}."  # TODO: make unit flexible
            )
            new_objects = self.set_height_relative_to_reference(
                new_objects,
                _new_exposure_geoms,
                elevation_reference,
                path_ref,
                attr_ref,
                new_area.set_index("object_id")["height"],
                self.crs,
            )

        # Update the exposure_geoms
        self.set_geom_names("new_development_area")
        self.set_exposure_geoms(_new_exposure_geoms)

        # If the user supplied aggregation area data, assign that to the
        # new composite areas
        if aggregation_area_fn is not None:
            new_objects, aggregated_objects_geoms, _ = join_exposure_aggregation_areas(
                _new_exposure_geoms.merge(new_objects, on="object_id"),
                aggregation_area_fn=aggregation_area_fn,
                attribute_names=attribute_names,
                label_names=label_names,
                new_composite_area=True,
            )
            # Update the exposure_geoms incl aggregation
            self.set_geom_names("new_development_area_aggregated")
            self.set_exposure_geoms(aggregated_objects_geoms)

            # Remove initial composite areas
            idx = self.geom_names.index("new_development_area")
            self.geom_names.pop(idx)
            self.exposure_geoms.pop(idx)

        # Update the exposure_db
        self.exposure_db = pd.concat([self.exposure_db, new_objects]).reset_index(
            drop=True
        )

    def link_exposure_vulnerability(
        self,
        exposure_linking_table: pd.DataFrame,
        damage_types: Optional[List[str]] = ["structure", "content"],
    ):
        if "Damage function name" not in exposure_linking_table.columns:
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
            # primary_object_type or secondary_object_type column in the exposure data
            # that the available column is used to link the exposure data to the
            # vulnerability data.
            len_diff_primary_linking_types = 100000
            len_diff_secondary_linking_types = 100000
            if "primary_object_type" in self.exposure_db.columns:
                unique_types_primary = set(self.get_primary_object_type())
                diff_primary_linking_types = unique_types_primary - unique_linking_types
                len_diff_primary_linking_types = len(diff_primary_linking_types)

            unique_types_secondary = set()
            if "secondary_object_type" in self.exposure_db.columns:
                unique_types_secondary = set(self.get_secondary_object_type())
                diff_secondary_linking_types = (
                    unique_types_secondary - unique_linking_types
                )
                len_diff_secondary_linking_types = len(diff_secondary_linking_types)

            # Check if the linking column is the primary_object_type or the Secondary
            # Object Type
            if (len(unique_types_primary) > 0) and (
                unique_types_primary.issubset(unique_linking_types)
            ):
                linking_column = "primary_object_type"
            elif (len(unique_types_secondary) > 0) and (
                unique_types_secondary.issubset(unique_linking_types)
            ):
                linking_column = "secondary_object_type"
            else:
                if (
                    len_diff_primary_linking_types < len_diff_secondary_linking_types
                ) and (len(unique_types_primary) > 0):
                    linking_column = "primary_object_type"
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
                    linking_column = "secondary_object_type"
                    self.logger.warning(
                        "There are "
                        f"{str(len(diff_secondary_linking_types))} "
                        "secondary_object_types that are not in the "
                        "linking table and will not have a damage "
                        f"function assigned for {damage_type} damages: "
                        f"{str(list(diff_secondary_linking_types))}"
                    )

            self.exposure_db[f"fn_damage_{damage_type}"] = self.exposure_db[
                linking_column
            ].map(linking_dict)

            self.logger.info(
                f"The {linking_column} was used to link the exposure data to the "
                f"vulnerability curves for {damage_type} damages."
            )

    def get_primary_object_type(self):
        if "primary_object_type" in self.exposure_db.columns:
            return list(self.exposure_db["primary_object_type"].unique())

    def get_secondary_object_type(self):
        if "secondary_object_type" in self.exposure_db.columns:
            return list(self.exposure_db["secondary_object_type"].unique())

    def get_max_potential_damage_columns(self) -> List[str]:
        """Returns the maximum potential damage columns in <exposure_db>

        Returns
        -------
        List[str]
            The maximum potential damage columns in <exposure_db>
        """
        return [c for c in self.exposure_db.columns if "max_damage_" in c]

    def set_max_potential_damage_columns(
        self, damage_types, damage_values, gdf, max_potential_damage
    ) -> None:
        """Calculate and set the maximum potential damage columns based on the provided damage types and values.

        Parameters
        ----------
        damage_types : list
            List of damage types for which the maximum potential damage should be calculated.
        damage_values : dict
            Dictionary containing the damage values for each building type and damage type.
        gdf : GeoDataFrame
            GeoDataFrame containing the primary_object_type and area information.
        max_potential_damage : str
            The maximum potential damage value.
        Returns
        -------
        None
        """
        for damage_type in damage_types:
            # Calculate the maximum potential damage for each object and per damage type
            try:
                self.exposure_db[f"max_damage_{damage_type}"] = [
                    damage_values[building_type][damage_type.lower()] * square_meters
                    for building_type, square_meters in zip(
                        gdf["primary_object_type"], gdf["area"]
                    )
                ]
            except KeyError as e:
                self.logger.warning(
                    f"Not found in the {max_potential_damage} damage "
                    f"value data: {e}"
                )

    def get_damage_function_columns(self) -> List[str]:
        """Returns the damage function columns in <exposure_db>

        Returns
        -------
        List[str]
            The damage function columns in <exposure_db>
        """
        return [c for c in self.exposure_db.columns if "fn_damage_" in c]

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
            Only select assets from this/these primary_object_type(s).
            Can be any primary_object_type in a list or 'all', by default None
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
                ~objects["primary_object_type"].isin(non_building_names), :
            ]

        if primary_object_type:
            if str(primary_object_type).lower() != "all":
                objects = objects.loc[
                    objects["primary_object_type"].isin([primary_object_type]), :
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
                ids = buildings["object_id"]
            elif selection_type == "aggregation_area":
                ids = buildings.loc[
                    buildings[f"Aggregation Label: {aggregation}"]
                    == aggregation_area_name,
                    "object_id",
                ]
        elif selection_type == "polygon":
            assert polygon_file is not None
            buildings = self.select_objects(
                primary_object_type=property_type,
                non_building_names=non_building_names,
                return_gdf=True,
            )
            polygon = gpd.read_file(polygon_file, engine="pyogrio").to_crs(
                buildings.crs
            )
            ids = gpd.sjoin(buildings, polygon)["object_id"]
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
                    "object_id": self.exposure_db["object_id"],
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
            # NOTE: This is only used for the transition time from old to new models and for the translation script!
            if "Object ID" in self.exposure_geoms[0].columns:
                assert set(self.exposure_geoms[0]["Object ID"]) == set(df["Object ID"])
            else:
                assert set(self.exposure_geoms[0]["object_id"]) == set(df["object_id"])
            df["geometry"] = self.exposure_geoms[0]["geometry"]
            gdf = gpd.GeoDataFrame(df, crs=self.exposure_geoms[0].crs)
        elif len(self.exposure_geoms) > 1:
            gdf_list = []
            for i in range(len(self.exposure_geoms)):
                if "Object ID" in self.exposure_geoms[i].columns:
                    gdf_list.append(
                        self.exposure_geoms[i].merge(df, on="Object ID", how="left")
                    )
                elif "object_id" in self.exposure_geoms[i].columns:
                    gdf_list.append(
                        self.exposure_geoms[i].merge(df, on="object_id", how="left")
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
                assert col.format("structure") in self.exposure_db.columns
            except AssertionError:
                print(f"Required variable column {col} not found in exposure data.")

    def set_height_relative_to_reference(
        self,
        exposure_to_modify: pd.DataFrame,
        exposure_geoms: gpd.GeoDataFrame,
        height_reference: str,
        path_ref: str,
        attr_ref: str,
        raise_by: Union[int, float, pd.Series],
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
        raise_by : Union[int, float, pd.Series]
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
            # must be sorted on the object_id.
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
            # Join the data based on "object_id"
            modified_objects_gdf = pd.merge(
                exposure_geoms,
                reference_table[["object_id", attr_ref]],
                on="object_id",
                how="left",
            )
            modified_objects_gdf = modified_objects_gdf.sort_values(
                by=["object_id"]
            ).set_index("object_id", drop=False)

        exposure_to_modify = exposure_to_modify.sort_values(by=["object_id"]).set_index(
            "object_id", drop=False
        )

        # Ensure that the raise_by variable has the correct type
        if not isinstance(raise_by, pd.Series):
            raise_by = pd.Series(raise_by, index=exposure_to_modify.index)

        # Find indices of properties that are below the required level
        properties_below_level = (
            exposure_to_modify.loc[:, "ground_flht"]
            + exposure_to_modify.loc[:, "ground_elevtn"]
            < modified_objects_gdf.loc[:, attr_ref] + raise_by
        )
        properties_no_reference_level = modified_objects_gdf[attr_ref].isna()
        to_change = properties_below_level & ~properties_no_reference_level

        self.logger.info(
            f"{properties_no_reference_level.sum()} properties have no "
            "reference height level. These properties are not raised."
        )

        original_df = exposure_to_modify.copy()  # to be used for metrics
        exposure_to_modify.loc[to_change, "ground_flht"] = list(
            modified_objects_gdf.loc[to_change, attr_ref]
            + raise_by[to_change]
            - exposure_to_modify.loc[to_change, "ground_elevtn"]
        )

        # Get some metrics on changes
        no_builds_to_change = sum(to_change)
        avg_raise = np.average(
            exposure_to_modify.loc[to_change, "ground_flht"]
            - original_df.loc[to_change, "ground_flht"]
        )
        self.logger.info(
            f"Raised {no_builds_to_change} properties with an average of {avg_raise}."
        )

        return exposure_to_modify.reset_index(drop=True)

    def update_user_linking_table(
        self,
        old_value: Union[list, str],
        new_value: Union[list, str],
        linking_table_new: pd.DataFrame,
    ):
        if isinstance(old_value, str):
            old_value = [old_value]
        if isinstance(new_value, str):
            new_value = [new_value]
        for item, new_item in zip(old_value, new_value):
            desired_rows = linking_table_new[linking_table_new["Exposure Link"] == item]
            desired_rows.reset_index(drop=True, inplace=True)
            linking_table_new = linking_table_new.append(
                desired_rows, ignore_index=True
            )
            duplicates_table = linking_table_new.duplicated(keep="first")
            idx_duplicates = duplicates_table[duplicates_table].index
            for idx in idx_duplicates:
                linking_table_new["Exposure Link"][idx:].replace(
                    {item: new_item}, inplace=True
                )
        return linking_table_new

    def get_continent(self):
        region = self.data_catalog.get_geodataframe("area_of_interest")
        lon = region.geometry[0].centroid.x
        lat = region.geometry[0].centroid.y

        geolocator = Nominatim(user_agent="<APP_NAME>", timeout=10)
        geocode = RateLimiter(geolocator.reverse, min_delay_seconds=1)

        location = geocode(f"{lat}, {lon}", language="en")

        # for cases where the location is not found, coordinates are antarctica
        if location is None:
            return "global", "global"

        # extract country code
        address = location.raw["address"]
        country_code = address["country_code"].upper()
        country_name = address["country"]

        # get continent code from country code
        continent_code = pc.country_alpha2_to_continent_code(country_code)
        continent_name = self.get_continent_name(continent_code)

        return country_name, continent_name

    def get_continent_name(self, continent_code: str) -> str:
        continent_dict = {
            "NA": "north america",
            "SA": "south america",
            "AS": "asia",
            "AF": "africa",
            "OC": "oceania",
            "EU": "europe",
            "AQ": "antarctica",
        }
        return continent_dict[continent_code]

    def unit_conversion(
        self, parameter: str, unit: Union[str, Units]
    ) -> Union[str, Units]:
        # Unit conversion
        if unit != self.unit:
            if (unit == Units.meters.value) and (self.unit == Units.feet.value):
                self.exposure_db[parameter] = self.exposure_db[parameter].apply(
                    lambda x: x * Conversion.meters_to_feet.value
                )

            elif (unit == Units.feet.value) and (self.unit == Units.meters.value):
                self.exposure_db[parameter] = self.exposure_db[parameter].apply(
                    lambda x: x * Conversion.feet_to_meters.value
                )
            else:
                self.logger.warning(
                    f"The {parameter} unit is not valid. Please provide the unit of your {parameter} in 'meters' or 'feet'"
                )
        else:
            pass

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
