from hydromt.data_catalog import DataCatalog
from hydromt_fiat.workflows.exposure import Exposure
import geopandas as gpd
import json


class ExposureVector(Exposure):
    _REQUIRED_COLUMNS = ["Object ID", "Extraction Method", "Ground Flood Height"]
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
        self.exposure = gpd.GeoDataFrame()
        self.source = gpd.GeoDataFrame()

    def setup_from_single_source(self, source: str) -> None:
        """_summary_

        Parameters
        ----------
        source : str
            _description_
        """
        if source == "NSI":
            source_data = self.data_catalog.get_geodataframe(source, geom=self.region)

            # Check if the 'fid' attribute can be used as unique ID
            if len(source_data.index) != len(set(source_data["fid"])):
                source_data[self.unique_id_attr] = range(1, len(source_data.index) + 1)

            # Read the json file that holds a dictionary of names of the NSI coupled to Delft-FIAT names
            with open(
                self.data_catalog.sources[source].kwargs["NSI_to_FIAT_translation_fn"]
            ) as json_file:
                nsi_fiat_translation = json_file.read()
            nsi_fiat_translation = json.loads(nsi_fiat_translation)

            # Fill the exposure data
            columns_to_fill = nsi_fiat_translation.keys()
            for column_name in columns_to_fill:
                self.exposure[column_name] = source_data[
                    nsi_fiat_translation[column_name]
                ]

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

    def setup_ground_floor_height(self):
        NotImplemented

    def setup_aggregation_labels(self):
        NotImplemented

    def get_occupancy_type1(self):
        if self.occupancy_type1_attr in self.exposure.columns:
            return list(self.exposure[self.occupancy_type1_attr].unique())

    def get_occupancy_type2(self):
        if self.occupancy_type2_attr in self.exposure.columns:
            return list(self.exposure[self.occupancy_type2_attr].unique())
