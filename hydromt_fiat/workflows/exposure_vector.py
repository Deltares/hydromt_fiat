from hydromt.data_catalog import DataCatalog
from hydromt_fiat.workflows.exposure import Exposure
import geopandas as gpd


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
        self, data_catalog: DataCatalog, config: dict, region: gpd.GeoDataFrame = None
    ):
        super().__init__(data_catalog=data_catalog, config=config, region=region)
        self.exposure = gpd.GeoDataFrame()
        self.source = gpd.GeoDataFrame()

    def setup_from_single_source(self):
        """
         column names NSI data:
         'fid', 'fd_id', 'bid', 'cbfips', 'st_damcat', 'occtype', 'bldgtype',
        'num_story', 'sqft', 'found_type', 'found_ht', 'med_yr_blt',
        'val_struct', 'val_cont', 'val_vehic', 'ftprntid', 'ftprntsrc',
        'source', 'students', 'pop2amu65', 'pop2amo65', 'pop2pmu65',
        'pop2pmo65', 'o65disable', 'u65disable', 'x', 'y', 'firmzone',
        'grnd_elv_m', 'ground_elv', 'id', 'geometry'
        """
        if self.config["asset_locations"] == "NSI":
            source = self.data_catalog.get_geodataframe(
                "NSI", variables=None, geom=self.region
            )

            # check if the 'fid' attribute can be used as unique ID
            if len(source.index) != len(set(source["fid"])):
                source[self.unique_id_attr] = range(1, len(source.index) + 1)

            # Fill the exposure data
            self.exposure["Object ID"] = source[self.unique_id_attr]
            self.exposure["Object Name"] = source[self.unique_id_attr]
            self.exposure["Primary Object Type"] = source[self.primary_object_type_attr]
            self.exposure["Secondary Object Type"] = source[
                self.secondary_object_type_attr
            ]
            self.exposure["Max Potential Damage: Structure"] = source[
                self.max_potential_damage_structure
            ]
            self.exposure["Max Potential Damage: Content"] = source[
                self.max_potential_damage_content
            ]
            self.exposure["Ground Elevation"] = source[self.ground_elevation_attr]

            # Multipoint to single point
            points = source[self.geometry_attr].apply(lambda x: x.geoms[0])
            self.exposure["X Coordinate"] = points.x
            self.exposure["Y Coordinate"] = points.y

        else:
            NotImplemented

    def setup_from_multiple_sources(self):
        NotImplemented

    def setup_asset_locations(self, asset_locations):
        self.exposure = asset_locations[[self.unique_id_attr, self.geometry_attr]]

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
