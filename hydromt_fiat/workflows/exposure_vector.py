from hydromt_fiat.workflows.vulnerability import Vulnerability
from hydromt_fiat.workflows.utils import detect_delimiter
from hydromt.data_catalog import DataCatalog
from hydromt_fiat.workflows.exposure import Exposure
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import json
from typing import Union, List, Any, Optional
import logging


class ExposureVector(Exposure):
    _REQUIRED_COLUMNS = ["Object ID", "Extraction Method", "Ground Floor Height"]
    _REQUIRED_VARIABLE_COLUMNS = ["Damage Function: {}", "Max Potential Damage: {}"]
    _OPTIONAL_COLUMNS = [
        "Object Name",
        "Primary Object Type",
        "Secondary Object Type",
        "X Coordinate",
        "Y Coordinate",
        "Ground Elevation",
        "Object-Location Shapefile Path",
        "Object-Location Join ID",
        "Join Attribute Field",
    ]
    _OPTIONAL_VARIABLE_COLUMNS = ["Aggregation Label: {}", "Aggregation Variable: {}"]

    _CSV_COLUMN_DATATYPES = {
        "Object ID": int,
        "Object Name": str,
        "Primary Object Type": str,
        "Secondary Object Type": str,
        "X Coordinate": float,
        "Y Coordinate": float,
        "Extraction Method": str,
        "Aggregation Label": str,
        "Damage Function: Structure": str,
        "Damage Function: Content": str,
        "Damage Function: Other": str,
        "Ground Flood Height": float,
        "Ground Elevation": float,
        "Max Potential Damage: Structure": float,
        "Max Potential Damage: Content": float,
        "Max Potential Damage: Other": float,
        "Object-Location Shapefile Path": str,
        "Object-Location Join ID": float,
        "Join Attribute Field": str,
    }

    def __init__(
        self,
        data_catalog: DataCatalog = None,
        region: gpd.GeoDataFrame = None,
        crs: str = None,
    ) -> None:
        """_summary_

        Parameters
        ----------
        data_catalog : DataCatalog, optional
            _description_, by default None
        region : gpd.GeoDataFrame, optional
            _description_, by default None
        crs : str, optional
            _description_, by default None
        """
        super().__init__(data_catalog=data_catalog, region=region, crs=crs)
        self.exposure_db = pd.DataFrame()
        self.exposure_geoms = gpd.GeoDataFrame()
        self.source = gpd.GeoDataFrame()

    def read(self, fn):
        # Read the exposure data.
        csv_delimiter = detect_delimiter(fn)
        self.exposure_db = pd.read_csv(
            fn, delimiter=csv_delimiter, dtype=self._CSV_COLUMN_DATATYPES, engine="c"
        )

    def setup_from_single_source(
        self, source: str, ground_floor_height: Union[int, float, str, None]
    ) -> None:
        """_summary_

        Parameters
        ----------
        source : str
            _description_
        """
        if source == "NSI":
            source_data = self.data_catalog.get_geodataframe(source, geom=self.region)
            source_data_authority = source_data.crs.to_authority()
            self.crs = source_data_authority[0] + ":" + source_data_authority[1]

            # Read the json file that holds a dictionary of names of the NSI coupled to Delft-FIAT names
            with open(
                self.data_catalog.sources[source].kwargs["NSI_to_FIAT_translation_fn"]
            ) as json_file:
                nsi_fiat_translation = json_file.read()
            nsi_fiat_translation = json.loads(nsi_fiat_translation)

            # Fill the exposure data
            columns_to_fill = nsi_fiat_translation.keys()
            for column_name in columns_to_fill:
                self.exposure_db[column_name] = source_data[
                    nsi_fiat_translation[column_name]
                ]

            # Check if the 'Object ID' column is unique
            if len(self.exposure_db.index) != len(set(self.exposure_db["Object ID"])):
                source_data["Object ID"] = range(1, len(self.exposure_db.index) + 1)

            self.setup_ground_floor_height(ground_floor_height)

            # Because NSI is used, the extraction method must be centroid
            self.setup_extraction_method("centroid")

        else:
            NotImplemented

    def setup_from_multiple_sources(self):
        NotImplemented

    def setup_asset_locations(self, asset_locations):
        NotImplemented

    def setup_occupancy_type(self):
        NotImplemented

    def setup_extraction_method(self, extraction_method: str) -> None:
        self.exposure_db["Extraction Method"] = extraction_method

    def setup_aggregation_labels(self):
        NotImplemented

    def setup_ground_floor_height(
        self,
        ground_floor_height: Union[int, float],
    ) -> None:
        # Set the ground floor height column.
        # If the Ground Floor Height is input as a number, assign all objects with
        # the same Ground Floor Height.
        if ground_floor_height:
            if type(ground_floor_height) == int or type(ground_floor_height) == float:
                self.exposure_db["Ground Floor Height"] = ground_floor_height
            elif type(ground_floor_height) == str:
                # TODO: implement the option to add the ground floor height from a file.
                NotImplemented
        else:
            # Set the Ground Floor Height to 0 if the user did not specify any
            # Ground Floor Height.
            self.exposure_db["Ground Floor Height"] = 0

    def setup_max_potential_damage(
        self,
        objectids: Union[List[int], str],
        damage_types: Union[List[str], str],
        max_potential_damage: Union[List[float], float],
    ):
        # TODO: implement that the max pot damage can be set from scratch from a single value or by doing a spatial join and taking from a column
        damage_cols = self.get_max_potential_damage_columns()

        print(damage_cols)
        NotImplemented
        # # The measure is to buy out selected properties. #TODO revise
        # logging.info(
        #     f"Setup the maximum potential damage of {len(objectids)} properties."
        # )

        # # Get the Object IDs to buy out
        # idx = self.get_object_ids(objectids=objectids)

        # # Get the columns that contain the maximum potential damage
        # if damage_types.lower() == "all":
        #     damage_cols = [
        #         c for c in self.exposure_db.columns if "Max Potential Damage:" in c
        #     ]
        # else:
        #     damage_cols = [f"Max Potential Damage: {t}" for t in damage_types]

        # # Set the maximum potential damage of the objects to buy out to zero
        # self.exposure_db[damage_cols].iloc[idx, :] = max_potential_damage

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
        logging.info(
            f"Updating the maximum potential damage of {len(updated_max_potential_damages.index)} properties."
        )
        if "Object ID" not in updated_max_potential_damages.columns:
            logging.warning(
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
            logging.warning(
                "Trying to update the Ground Floor Height but the attribute does not yet exist in the exposure data."
            )
            return

        # Get the index of the objects to raise the ground floor height.
        idx = self.exposure_db.loc[self.exposure_db["Object ID"].isin(objectids)].index

        # Log the number of objects that are being raised.
        logging.info(
            f"Setting the ground floor height of {len(idx)} properties to {raise_by}."
        )

        if height_reference.lower() == "datum":
            # Elevate the object with 'raise_to'
            logging.info(
                "Setting the ground floor height of the properties relative to Datum."
            )
            self.exposure_db.loc[
                self.exposure_db["Ground Floor Height"] < raise_by,
                "Ground Floor Height",
            ].iloc[idx, :] = raise_by

        elif height_reference.lower() == "geom":
            # Elevate the objects relative to the surface water elevation map that the user submitted.
            logging.info(
                f"Setting the ground floor height of the properties relative to {Path(path_ref).stem}, with column {attr_ref}."
            )

            self.get_geoms_from_xy()  # TODO see if this can only be done once when necessary
            self.exposure_db.iloc[idx, :] = self.set_height_relative_to_reference(
                self.exposure_db.iloc[idx, :],
                path_ref,
                attr_ref,
                raise_by,
                self.crs,
            )

        elif height_reference.lower() == "table":
            # Input a CSV with Object IDs and elevations
            NotImplemented

        else:
            logging.warning(
                f"The height reference of the Ground Floor Height is set to '{height_reference}'. "
                "This is not one of the allowed height references. Set the height reference to 'datum', 'geom' or 'raster' (last option not yet implemented)."
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
        logging.info(
            f"Floodproofing {len(objectids)} properties for {floodproof_to} ft (CHANGE TO UNIT) of water."
        )  # TODO: change ft to unit

        # The user can submit with how much feet the properties should be floodproofed and the damage function
        # is truncated to that level.
        df_name_suffix = f'_fp_{str(floodproof_to).replace(".", "_")}'

        ids = self.get_object_ids(selection_type="list", objectids=objectids)
        idx = self.exposure_db.loc[self.exposure_db["Object ID"].isin(ids)].index

        # Find all damage functions that should be modified and truncate with floodproof_to.
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

        # Calculate the Max. Potential Damages for the new area. This is the total percentage of population growth
        # multiplied with the total sum of the Max Potential Structural/Content/Other Damage.
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
        logging.info(
            f"Adding a new exposure object with a value of {percent_growth}% "
            "of the current total exposure objects, using the "
            f"geometry/geometries from {geom_file}."
        )

        percent_growth = float(percent_growth) / 100
        geom_file = Path(geom_file)
        assert geom_file.is_file()

        # Calculate the total damages for the new object, for the indicated damage types.
        new_object_damages = self.calculate_damages_new_exposure_object(
            percent_growth, damage_types
        )

        # Read the original damage functions and create new weighted damage functions from the original ones.
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
        new_area = gpd.read_file(geom_file)
        # check_crs(new_area, geom_file)  #TODO implement again
        new_objects = []

        # Calculate the total area to use for adding the damages relative to area
        total_area = (
            new_area.geometry.area.sum()
        )  # TODO: reproject to a projected CRS if this is a geographic CRS?

        # There should be an attribute 'FID' in the new development area shapefile. This ID is used to join the
        # shapefile to the exposure data.
        join_id_name = "FID"
        if join_id_name not in new_area.columns:
            logging.info(
                'The unique ID column in the New Development Area is not named "FID", therefore, a new unique identifyer named "FID" is added.'
            )
            new_area[join_id_name] = range(len(new_area.index))
            new_area.to_file(geom_file)

        max_id = self.exposure_db["Object ID"].max()
        for i in range(len(new_area.index)):
            perc_damages = new_area.geometry.iloc[i].area / total_area
            # TODO: Alert the user that the ground elevation is set to 0.
            # Take ground elevation from DEM?
            # For water level calculation this will not take into account the non-flooded cells separately, just averaged
            # Reduction factor for the part of the area is not build-up?
            dict_new_objects_data = {
                "Object ID": [max_id + 1],
                "Object Name": ["New development area: " + str(max_id + 1)],
                "Primary Object Type": ["New development area"],
                "Secondary Object Type": ["New development area"],
                "Extraction Method": ["AREA"],
                "Ground Floor Height": [0],
                "Ground Elevation": [0],
                "Object-Location Shapefile Path": [str(geom_file)],
                "Object-Location Join ID": [new_area["FID"].iloc[i]],
                "Join Attribute Field": [join_id_name],
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
            max_id += 1

        new_objects = pd.concat(new_objects)
        new_objects.reset_index(inplace=True)

        if elevation_reference == "datum":
            new_objects["Ground Floor Height"] = ground_floor_height
            logging.info(
                f"The elevation of the new development area is {ground_floor_height} ft"
                " relative to datum."  # TODO: make unit flexible
            )
        elif elevation_reference == "geom":
            logging.info(
                f"The elevation of the new development area is {ground_floor_height} ft"
                f" relative to {Path(path_ref).stem}. The height of the floodmap is"
                f" identified with column {attr_ref}."  # TODO: make unit flexible
            )
            new_objects = self.set_height_relative_to_reference(
                new_objects,  # TODO: Change to a GeoPandas dataframe
                path_ref,
                attr_ref,
                ground_floor_height,
                self.crs,
            )

        self.exposure_db = pd.concat([self.exposure_db, new_objects])

    def link_exposure_vulnerability(self, exposure_linking_table: pd.DataFrame):
        linking_dict = dict(
            zip(exposure_linking_table["Link"], exposure_linking_table["Name"])
        )
        self.exposure_db["Damage Function: Structure"] = self.exposure_db[
            "Secondary Object Type"
        ].map(linking_dict)

    def get_primary_object_type(self):
        if "Primary Object Type" in self.exposure_db.columns:
            return list(self.exposure_db["Primary Object Type"].unique())

    def get_secondary_object_type(self):
        if "Secondary Object Type" in self.exposure_db.columns:
            return list(self.exposure_db["Secondary Object Type"].unique())

    def get_max_potential_damage_columns(self):
        return [c for c in self.exposure_db.columns if "Max Potential Damage:" in c]

    def get_damage_function_columns(self):
        return [c for c in self.exposure_db.columns if "Damage Function:" in c]

    def select_objects(
        self,
        type: Optional[str] = None,
        non_building_names: Optional[list[str]] = None,
        return_gdf: bool = False,
    ) -> gpd.GeoDataFrame:
        objects = self.exposure_db

        if non_building_names:
            objects = objects.loc[
                ~objects["Primary Object Type"].isin(non_building_names), :
            ]

        if type:
            if str(type).lower() != "all":
                objects = objects.loc[objects["Primary Object Type"] == type, :]

        if return_gdf:
            objects = self.df_to_gdf(objects, crs=self.crs)

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
        Returns
        -------
        list[Any]
            list of ids
        """
        if (selection_type == "aggregation_area") or (selection_type == "all"):
            buildings = self.select_objects(
                type=property_type,
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
                type=property_type,
                non_building_names=non_building_names,
                return_gdf=True,
            )
            polygon = gpd.read_file(polygon_file)
            ids = gpd.sjoin(buildings, polygon)["Object ID"]
        elif selection_type == "list":
            ids = objectids

        return ids

    def get_geoms_from_xy(self):
        # TODO see if and how this can be merged with the df_to_gdf function
        exposure_geoms = gpd.GeoDataFrame(
            {
                "Object ID": self.exposure_db["Object ID"],
                "geometry": gpd.points_from_xy(
                    self.exposure_db["X Coordinate"], self.exposure_db["Y Coordinate"]
                ),
            }
        )
        self.exposure_geoms = exposure_geoms

    @staticmethod
    def df_to_gdf(df: pd.DataFrame, crs: str) -> gpd.GeoDataFrame:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["X Coordinate"], df["Y Coordinate"]),
            crs=crs,
        )
        return gdf

    def check_required_columns(self):
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
        exposure_to_modify: gpd.GeoDataFrame,
        path_ref: str,
        attr_ref: str,
        raise_by: Union[int, float],
        out_crs,
    ) -> gpd.GeoDataFrame:
        """
        Note: It is assumed that the datum/DEM with which the geom file is created is the same as that of the exposure data
        """
        # Add the different options of input data: vector, raster, table
        reference_shp = gpd.read_file(path_ref)  # Vector

        # Reproject the input flood map if necessary
        if str(reference_shp.crs).upper() != str(out_crs).upper():
            reference_shp = reference_shp.to_crs(out_crs)

        # Spatially join the data
        modified_objects_gdf = gpd.sjoin(
            exposure_to_modify,  # TODO: change to the exposure objects that should be modified, check if this is the correct variable.
            reference_shp[[attr_ref, "geometry"]],
            how="left",
        )
        modified_objects_gdf["value"] = modified_objects_gdf[attr_ref]

        # Sort and add the elevation to the shp values, append to the exposure dataframe.
        # To be able to append the values from the GeoDataFrame to the DataFrame, it must be sorted on the Object ID.
        modified_objects_gdf = (
            modified_objects_gdf.groupby("Object ID")
            .max("value")
            .sort_values(by=["Object ID"])
        )
        exposure_to_modify = exposure_to_modify.sort_values(by=["Object ID"]).set_index(
            "Object ID", drop=False
        )

        # Find indices of properties that are bellow the required level
        to_change = (
            exposure_to_modify.loc[:, "Ground Floor Height"]
            + exposure_to_modify.loc[:, "Ground Elevation"]
            < modified_objects_gdf.loc[:, "value"] + raise_by
        )
        original_df = exposure_to_modify.copy()  # to be used for metrics
        exposure_to_modify.loc[to_change, "Ground Floor Height"] = list(
            modified_objects_gdf.loc[to_change, "value"]
            + raise_by
            - exposure_to_modify.loc[to_change, "Ground Elevation"]
        )

        # Get some metrics on changes
        no_builds_to_change = sum(to_change)
        avg_raise = np.average(
            exposure_to_modify.loc[to_change, "Ground Floor Height"]
            - original_df.loc[to_change, "Ground Floor Height"]
        )
        logging.info(
            f"Raised {no_builds_to_change} properties with an average of {avg_raise}."
        )

        return exposure_to_modify.reset_index(drop=True)
