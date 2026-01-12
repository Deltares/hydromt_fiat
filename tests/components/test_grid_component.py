import logging
from unittest.mock import MagicMock

import geopandas as gpd
import numpy as np
import pytest
import xarray as xr
from pyproj.crs import CRS

from hydromt_fiat.components.grid import GridCustomComponent

# Overwrite the abstractmethods to be able to initialize it
GridCustomComponent.__abstractmethods__ = set()


def test_grid_custom_component_clear(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert len(component.data.data_vars) == 1

    # Call the clear method
    component.clear()
    # Assert the state after
    assert len(component.data.data_vars) == 0


def test_grid_custom_component_clip(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (34, 25)

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small, buffer=0)
    # Assert the output
    assert ds.flood_event.shape == (5, 4)


def test_grid_custom_component_clip_no_data(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)
    # Assert the current state
    assert component._data is None

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small)
    # Assert that there is no output
    assert ds is None


def test_grid_custom_component_clip_inplace(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (34, 25)

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small, buffer=0, inplace=True)
    # Assert that the output is None but the shape of the component data changed
    assert ds is None
    assert component.data.flood_event.shape == (5, 4)


def test_grid_custom_component_reproject(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (34, 25)
    assert component.crs.to_epsg() == 28992
    np.testing.assert_almost_equal(component.data.x.values[0], 85250)

    # Reproject the data
    ds = component.reproject(crs=4326)

    # Assert the output
    assert not component.data.equals(ds)
    assert component.crs.to_epsg() == 28992
    assert ds.raster.crs.to_epsg() == 4326
    assert ds.flood_event.shape == (28, 33)
    np.testing.assert_almost_equal(ds.longitude.values[0], 4.371, decimal=3)


def test_grid_custom_component_reproject_inplace(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (34, 25)
    assert component.crs.to_epsg() == 28992

    # Reproject inplace
    ds = component.reproject(crs=CRS.from_epsg(4326), inplace=True)

    # Assert the output/ state
    assert ds is None
    assert component.crs.to_epsg() == 4326
    assert component.data.flood_event.shape == (28, 33)


def test_grid_custom_component_reproject_nothing(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    id_before = id(component.data)  # To check later

    # Reproject with the same crs
    ds = component.reproject(crs="EPSG:28992")
    # Assert the state/ output
    assert ds is None
    assert id_before == id(component.data)

    # Same yields true when the data crs is None
    component._data = component._data.drop("spatial_ref")
    id_before = id(component.data)  # To check later

    # Reproject with the same crs
    ds = component.reproject(crs="EPSG:4326")
    # Assert the state/ output
    assert ds is None
    assert id_before == id(component.data)


def test_grid_custom_component_set(
    mock_model: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)
    # Assert nothing in the component
    assert len(component.data.data_vars) == 0

    # Set the data via the set method, providing a dataset
    component.set(exposure_grid_clipped)

    # Assert the state
    assert len(component.data.data_vars) == 4
    assert "commercial_content" in component.data.data_vars

    # Set data as a dataarray
    component.set(exposure_grid_clipped["commercial_content"], name="foo")

    # Assert the state
    assert len(component.data.data_vars) == 5
    assert "foo" in component.data.data_vars


def test_grid_custom_component_set_replace(
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    caplog.set_level(logging.WARNING)
    # Set up the component
    component = GridCustomComponent(model=mock_model)
    # Assert nothing in the component
    assert len(component.data.data_vars) == 0

    # Set the data via the set method, providing a dataset
    component.set(exposure_grid_clipped)
    component.set(exposure_grid_clipped)

    # Assert the logging message
    assert "Replacing grid map: 'commercial_content'" in caplog.text

    # Assert the state
    assert len(component.data.data_vars) == 4  # not 8
    assert "commercial_content" in component.data.data_vars


def test_grid_custom_component_set_errors(
    mock_model: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Set up the component
    component = GridCustomComponent(model=mock_model)

    # Dataarray without a name
    da = exposure_grid_clipped["commercial_content"]
    da.name = None
    with pytest.raises(
        ValueError,
        match="DataArray can't be set without a name",
    ):
        component.set(da)

    # Wrong input data type, nonsense like an integer
    with pytest.raises(
        TypeError,
        match="Wrong input data type: 'int'",
    ):
        component.set(2)
