import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import numpy as np
import pytest
from hydromt.model import ModelRoot
from pyproj.crs import CRS
from shapely.geometry import MultiPolygon, Polygon

from hydromt_fiat.components import RegionComponent
from hydromt_fiat.utils import REGION


def test_region_component_empty(mock_model: MagicMock):
    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)

    # assert that it is empty
    assert component.data is None
    assert component._filename == f"{REGION}.geojson"


def test_region_component_clear(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
):
    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)

    # Set the data like a dummy
    component._data = build_region_small
    # Assert the current state
    assert component.data is not None
    assert isinstance(component.data, gpd.GeoDataFrame)

    # Call the clear method
    component.clear()
    # Assert the state after
    assert component.data is None


def test_region_component_reproject(
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)
    # Set data like a dummy
    component._data = build_region
    # Assert the current state
    assert component.crs.to_epsg() == 4326
    np.testing.assert_almost_equal(
        component.data.exterior[0].xy[0][0],
        desired=4.384,
        decimal=3,
    )

    # Reproject the region
    component.reproject(crs=28992)
    # Assert the state
    assert component.crs.to_epsg() == 28992
    np.testing.assert_almost_equal(
        component.data.exterior[0].xy[0][0],
        desired=86046.470,
        decimal=3,
    )


def test_region_component_reproject_nothing(
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)
    # Set data like a dummy
    component._data = build_region
    # Assert the current state
    assert component.crs.to_epsg() == 4326
    id_before = id(component.data)  # For checking if the same later

    # Reproject with same CRS
    component.reproject(crs=CRS.from_epsg(4326))
    # Assert the id's are the same, i.e. nothing happened
    assert id_before == id(component.data)


def test_region_component_set(
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
    build_region_small: gpd.GeoDataFrame,
):
    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)

    # Add a geometry
    component.set(build_region)

    # Assert that there is data
    assert isinstance(component.data, gpd.GeoDataFrame)
    assert component.region is not None
    assert len(component.region.columns) == 1
    assert component.region.crs.to_epsg() == 4326

    # Empty the component and assert that crs is adjusted based on the model
    component._data = None
    component.model.crs = None  # Normally this would reset the crs
    assert build_region_small.crs.to_epsg() == 28992
    component.set(build_region_small)
    assert component.region.crs.to_epsg() == 28992


def test_region_component_set_series(
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)
    # Assert the current state
    assert component.region is None

    # Assert that a GeoSeries is sufficient as input
    component.set(build_region.geometry)
    assert component.region is not None
    assert isinstance(component.data, gpd.GeoDataFrame)


def test_region_component_set_replace(
    mock_model: MagicMock,
    box_geometry: gpd.GeoDataFrame,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)
    component.set(build_region)
    assert isinstance(component.region.geometry[0], Polygon)

    # Add a polygon that will enter a union with the current region
    component.set(box_geometry, replace=True)

    # Assert
    assert len(component.data) == 1
    assert isinstance(component.region.geometry[0], Polygon)


def test_region_component_set_union(
    mock_model: MagicMock,
    box_geometry: gpd.GeoDataFrame,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component with the mock model
    component = RegionComponent(model=mock_model)
    component.set(build_region)
    assert isinstance(component.region.geometry[0], Polygon)

    # Add a polygon that will enter a union with the current region
    component.set(box_geometry)

    # Assert
    assert len(component.data) == 1
    assert isinstance(component.region.geometry[0], MultiPolygon)


def test_region_component_read(
    tmp_path: Path,
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="r"),
    )
    component = RegionComponent(model=mock_model)
    component.read()
    assert component.data is None
    assert component.region is None

    # Write the region gdf to the tmp directory
    build_region.to_file(Path(tmp_path, f"{REGION}.geojson"))

    # Re-read
    component.read()
    assert component.data is not None
    assert component.region is not None


def test_region_component_write_empty(
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
):
    caplog.set_level(logging.DEBUG)

    # Setup component and a region
    component = RegionComponent(model=mock_model)

    # Empty write
    component.write()
    assert "No region data found, skip writing." in caplog.text

    # Write empty region GeoDataFrame
    component._data = gpd.GeoDataFrame()
    component.write()
    assert "Region is empty. Skipping..." in caplog.text


def test_region_component_write_default(
    tmp_path: Path,
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component
    component = RegionComponent(model=mock_model)

    # Set something in the component
    component.set(build_region)
    # Write the data
    component.write()
    assert Path(tmp_path, f"{REGION}.geojson").is_file()

    # Write to separate directory
    component.write(filename=f"geom/{REGION}.geojson")
    assert Path(tmp_path, "geom").is_dir()
    component = None


def test_region_component_write_crs(
    tmp_path: Path,
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
):
    # Create new component
    # Adjust the model crs to test the write capabilities
    type(mock_model).crs = PropertyMock(side_effect=lambda: CRS.from_epsg(28992))
    component = RegionComponent(model=mock_model)

    # Set the component with a geometry in a local projection
    component.set(build_region_small)
    assert component.region.crs.to_epsg() == 28992

    # Write and assert output
    component.write()
    gdf = gpd.read_file(Path(tmp_path, f"{REGION}.geojson"))
    assert gdf.crs.to_epsg() == 28992
    gdf = None
    # Check that the to_wgs84 works
    component.write(to_wgs84=True)
    gdf = gpd.read_file(Path(tmp_path, f"{REGION}.geojson"))
    assert gdf.crs.to_epsg() == 4326
