from unittest.mock import PropertyMock

import geopandas as gpd
from hydromt.model import ModelRoot
from pyproj.crs import CRS
from shapely.geometry import MultiPolygon, Polygon, box

from hydromt_fiat.components import RegionComponent


def test_region_component(tmp_path, build_region_gdf, mock_model):
    # Set the neccessary attributes to ensure it runs
    type(mock_model).crs = PropertyMock(side_effect=lambda: CRS.from_epsg(4326))
    type(mock_model).root = PropertyMock(side_effect=lambda: ModelRoot(tmp_path))

    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)

    # assert that it is empty
    assert len(component.data) == 0
    assert component._filename == "region.geojson"

    # Add a geometry
    component.set(build_region_gdf)

    # Assert that there is data
    assert "region" in component.data
    assert len(component.data) == 1
    assert component.region is not None
    assert len(component.region.columns) == 1

    # Write the data
    component.write()
    component = None

    # Initialize another component
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="r"),
    )
    component_new = RegionComponent(model=mock_model)

    # Assert that there is a region present
    assert component_new.region is not None
    assert isinstance(component_new.region.geometry[0], Polygon)

    # Add a polygon that will enter a union with the current region
    new_geom = gpd.GeoDataFrame(
        geometry=[box(4.355, 52.035, 4.365, 52.045)],
        crs=4326,
    )
    component_new.set(new_geom)

    # Assert
    assert len(component_new.data) == 1
    assert isinstance(component_new.region.geometry[0], MultiPolygon)
