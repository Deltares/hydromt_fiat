import logging
from unittest.mock import MagicMock

import geopandas as gpd
import numpy as np
import pytest
from pyproj.crs import CRS

from hydromt_fiat.components.geom import GeomsComponent

# Overwrite the abstractmethods to be able to initialize it
GeomsComponent.__abstractmethods__ = set()


def test_geoms_component_empty(
    mock_model: MagicMock,
):
    # Set up the component
    component = GeomsComponent(model=mock_model)

    # Assert the current state
    assert component._data is None
    assert isinstance(component.data, dict)  # After initializing
    assert len(component.data) == 0


def test_geoms_component_clear(
    mock_model: MagicMock,
    exposure_vector: gpd.GeoDataFrame,
):
    # Set up the component
    component = GeomsComponent(model=mock_model)

    # Set data like a dummy
    component._data = {"foo": exposure_vector}
    # Assert the current state, i.e. amount of rows
    assert len(component.data) == 1

    # Call the clear method
    component.clear()
    # Assert the state after
    assert len(component.data) == 0


def test_geoms_component_clip(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    exposure_vector: gpd.GeoDataFrame,
):
    # Set up the component
    component = GeomsComponent(model=mock_model)

    # Set data like a dummy
    component._data = {"foo": exposure_vector}
    # Assert the current state, i.e. amount of rows
    assert component.data["foo"].shape[0] == 543
    # Assert equal crs
    assert exposure_vector.crs == build_region_small.crs

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small)
    # Assert the output
    assert ds["foo"].shape[0] == 12


def test_geoms_component_clip_srs(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    exposure_vector: gpd.GeoDataFrame,
):
    # Set up the component
    component = GeomsComponent(model=mock_model)

    # Set data like a dummy
    component._data = {"foo": exposure_vector}
    # Assert the current state, i.e. amount of rows
    assert component.data["foo"].shape[0] == 543

    # Reproject the region
    build_region_small.to_crs(4326, inplace=True)
    # Assert that the crs is not equal
    assert exposure_vector.crs != build_region_small.crs

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small)
    # Assert the output
    assert ds["foo"].shape[0] == 12


def test_geoms_component_clip_no_data(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
):
    # Set up the component
    component = GeomsComponent(model=mock_model)
    # Assert the current state
    assert component._data is None

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small)
    # Assert that there is no output
    assert ds is None


def test_geoms_component_clip_inplace(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    exposure_vector: gpd.GeoDataFrame,
):
    # Set up the component
    component = GeomsComponent(model=mock_model)

    # Set data like a dummy
    component._data = {"foo": exposure_vector}
    # Assert the current state
    assert component.data["foo"].shape[0] == 543

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small, inplace=True)
    # Assert that the output is None but the shape of the component data changed
    assert ds is None
    assert component.data["foo"].shape[0] == 12


def test_geoms_component_reproject(
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component
    component = GeomsComponent(model=mock_model)
    # Set data like a dummy
    component._data = {"ds1": build_region}
    # Assert the current state
    assert component.data["ds1"].crs.to_epsg() == 4326
    np.testing.assert_almost_equal(
        component.data["ds1"].exterior[0].xy[0][0], desired=4.384, decimal=3
    )

    # Call the reproject method
    ds = component.reproject(crs=28992)
    # Assert the output
    assert ds["ds1"].crs.to_epsg() == 28992
    np.testing.assert_almost_equal(
        ds["ds1"].exterior[0].xy[0][0], desired=86046.470, decimal=3
    )


def test_geoms_component_reproject_inplace(
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component
    component = GeomsComponent(model=mock_model)
    # Set data like a dummy
    component._data = {"ds1": build_region}
    # Assert the current state
    assert component.data["ds1"].crs.to_epsg() == 4326
    np.testing.assert_almost_equal(
        component.data["ds1"].exterior[0].xy[0][0], desired=4.384, decimal=3
    )

    # Call the reproject method
    ds = component.reproject(crs=CRS.from_epsg(28992), inplace=True)
    # Assert the output
    assert ds is None
    assert component.data["ds1"].crs.to_epsg() == 28992
    np.testing.assert_almost_equal(
        component.data["ds1"].exterior[0].xy[0][0], desired=86046.470, decimal=3
    )


def test_geoms_component_reproject_nothing(
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    # Setup the component
    component = GeomsComponent(model=mock_model)
    # Set data like a dummy
    component._data = {"ds1": build_region}
    # Assert the current state
    assert component.data["ds1"].crs.to_epsg() == 4326
    id_before = id(component.data["ds1"])

    # Call the reproject method
    ds = component.reproject(crs="EPSG:4326")
    # Assert the output
    assert ds["ds1"].crs.to_epsg() == 4326  # Still
    assert id_before == id(ds["ds1"])  # Same dataset, nothing happened


def test_geoms_component_set(
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = GeomsComponent(model=mock_model)
    assert len(component.data) == 0  # No data yet

    # Add a geometry dataset
    component.set(data=build_region, name="ds1")

    # Assert that it's there
    assert len(component.data) == 1
    assert "ds1" in component.data

    # Overwrite with the same dataset, should produce no warning
    component.set(data=build_region, name="ds1")
    assert "Replacing geom: ds1" not in caplog.text

    # Overwrite, but with a copy, should produce a warning
    component.set(data=build_region.copy(), name="ds1")
    assert "Replacing geom: ds1" in caplog.text


def test_geoms_component_region(
    build_region: gpd.GeoDataFrame,
    box_geometry: gpd.GeoDataFrame,
    mock_model: MagicMock,
):
    # Setup the component
    component = GeomsComponent(model=mock_model)
    assert component.region is None

    # Set a second dataset
    component.set(data=build_region, name="ds1")

    # Assert the content
    assert component.region is not None
    np.testing.assert_array_almost_equal(
        component.region.total_bounds,
        [4.371, 51.966, 4.408, 51.997],
        decimal=3,
    )

    # Add a second geometry to lying completely outside of the first one
    component.set(data=box_geometry, name="ds2")

    # Assert the region is larger now, eye test
    np.testing.assert_array_almost_equal(
        component.region.total_bounds,
        [4.355, 51.966, 4.408, 52.045],
        decimal=3,
    )
