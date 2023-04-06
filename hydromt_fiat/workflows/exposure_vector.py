from hydromt.data_catalog import DataCatalog
from hydromt_fiat.workflows.exposure import Exposure
import geopandas as gpd
import pandas as pd
import json
import geopandas as gpd
import json
from typing import Union


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
        self, data_catalog: DataCatalog, region: gpd.GeoDataFrame = None
    ) -> None:
        """_summary_

        Parameters
        ----------
        data_catalog : DataCatalog
            _description_
        region : gpd.GeoDataFrame, optional
            _description_, by default None
        """
        super().__init__(data_catalog=data_catalog, region=region)
        self.exposure_db = pd.DataFrame()
        self.exposure_geoms = gpd.GeoDataFrame()
        self.source = gpd.GeoDataFrame()
        self.crs = ""

    def read(self, fn):
        # Read the exposure data and create a modified exposure dataframe.
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

    def setup_max_potential_damage(self):
        NotImplemented

    def setup_extraction_method(self, extraction_method):
        self.exposure_db["Extraction Method"] = extraction_method

    def setup_ground_floor_height(self, ground_floor_height):
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

    def setup_aggregation_labels(self):
        NotImplemented

    def get_occupancy_type1(self):
        if self.occupancy_type1_attr in self.exposure_db.columns:
            return list(self.exposure_db[self.occupancy_type1_attr].unique())

    def get_occupancy_type2(self):
        if self.occupancy_type2_attr in self.exposure_db.columns:
            return list(self.exposure_db[self.occupancy_type2_attr].unique())

    def link_exposure_vulnerability(self, exposure_linking_table: pd.DataFrame):
        linking_dict = dict(
            zip(exposure_linking_table["Link"], exposure_linking_table["Name"])
        )
        self.exposure_db["Damage Function: Structure"] = self.exposure_db[
            "Secondary Object Type"
        ].map(linking_dict)

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


def detect_delimiter(csvFile):
    """From stackoverflow
    https://stackoverflow.com/questions/16312104/can-i-import-a-csv-file-and-automatically-infer-the-delimiter
    """
    with open(csvFile, "r") as myCsvfile:
        header = myCsvfile.readline()
        if header.find(";") != -1:
            return ";"
        if header.find(",") != -1:
            return ","
    # default delimiter (MS Office export)
    return ";"
