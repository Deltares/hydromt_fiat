"""Define custom components."""

from typing import Optional

import geopandas as gpd
from hydromt.model.components import GeomsComponent


class RegionComponent(GeomsComponent):
    """Custom component for region.

    Parameters
    ----------
    model: Model
        HydroMT model instance
    filename: str
        The path to use for reading and writing of component data by default.
        by default "geoms/{name}.geojson" i.e.
        one file per geodataframe in the data dictionary.
    region_component: str, optional
        The name of the region component to use as reference for this component's
        region. If None, the region will be set to the union of all geometries in
        the data dictionary.
    region_filename: str
        The path to use for writing the region data to a file. By default
        "geoms/geoms_region.geojson".
    """

    @property
    def _region_data(self) -> Optional[gpd.GeoDataFrame]:
        # Use the total bounds of all geometries as region
        if len(self.data) == 0:
            return None
        if "region" not in self.data:
            return None

        return self.data["region"]
