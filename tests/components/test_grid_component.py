import logging
import re
from unittest.mock import MagicMock

import geopandas as gpd
import numpy as np
import pytest
import xarray as xr
from pyproj.crs import CRS
from pytest_mock import MockerFixture

from hydromt_fiat.components.grid import GridComponent
from hydromt_fiat.errors import MissingRegionError

# Overwrite the abstractmethods to be able to initialize it
GridComponent.__abstractmethods__ = set()


def test_grid_component_empty(mock_model: MagicMock):
    # Set up the component
    component = GridComponent(model=mock_model("grid"))

    # Assert the state
    assert component._data is None
    assert isinstance(component.data, xr.Dataset)  # Initialized

    # Assert the properties
    assert component._region_data is None
    assert component.bounds is None
    assert component.crs is None
    assert component.like is None
    assert component.res is None
    assert component.transform is None


def test_grid_component__assert_entry(
    mock_model: MagicMock,
):
    # Set up the component
    component = GridComponent(model=mock_model)

    # Set data like a dummy
    component._data = xr.Dataset(data_vars={"foo": xr.DataArray()})

    # Assert it's fine to call foo
    component._assert_entry(name="foo")


def test_grid_component__assert_entry_errors(
    mock_model: MagicMock,
):
    # Set up the component
    component = GridComponent(model=mock_model)
    # Set data like a dummy
    component._data = xr.Dataset(data_vars={"foo": xr.DataArray()})

    # Data name not present
    with pytest.raises(
        RuntimeError,
        match=re.escape("Choose from already present data variables: ['foo']"),
    ):
        component._assert_entry(name="baz", spatial=False)

    # Data name not present
    with pytest.raises(
        RuntimeError,
        match=re.escape("Choose from already present data variables: []"),
    ):
        component._assert_entry(name="baz", spatial=True)


def test_grid_component__assert_model_type(
    mock_model: MagicMock,
):
    # Set up the component
    component = GridComponent(model=mock_model("grid"))

    # Assert it's fine to call
    flag = component._assert_model_type()

    # Assert the flag
    assert flag


def test_grid_component__assert_model_type_false(
    mock_model: MagicMock,
):
    # Set up the component
    component = GridComponent(model=mock_model("geom"))

    # Assert it's fine to call
    flag = component._assert_model_type(error=False)

    # Assert the flag
    assert not flag


def test_grid_component__assert_model_type_errors(
    mock_model: MagicMock,
):
    # Set up the component
    component = GridComponent(model=mock_model("geom"))

    # Assert it errors
    with pytest.raises(
        TypeError,
        match="Model is in the wrong type",
    ):
        _ = component._assert_model_type()


def test_grid_component_properties(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard

    # Assert properties when data is present
    assert isinstance(component._region_data, gpd.GeoDataFrame)
    np.testing.assert_array_almost_equal(
        component.bounds,
        [85100, 442400, 87800, 445900],
    )
    assert component.crs.to_epsg() == 28992
    np.testing.assert_array_almost_equal(
        component.res,
        (100, -100),
    )
    np.testing.assert_array_almost_equal(
        component.transform,
        (100, 0, 85100, 0, -100, 445900, 0, 0, 1),
    )


def test_grid_component_clear(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model("grid"))

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert len(component.data.data_vars) == 1

    # Call the clear method
    component.clear()
    # Assert the state after
    assert len(component.data.data_vars) == 0


def test_grid_component_clip(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (35, 27)

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small, buffer=0)
    # Assert the output
    assert ds.flood_event.shape == (5, 4)


def test_grid_component_clip_no_data(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
):
    # Set up the component
    component = GridComponent(model=mock_model("grid"))
    # Assert the current state
    assert component._data is None

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small)
    # Assert that there is no output
    assert ds is None


def test_grid_component_clip_inplace(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (35, 27)

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small, buffer=0, inplace=True)
    # Assert that the output is None but the shape of the component data changed
    assert ds is None
    assert component.data.flood_event.shape == (5, 4)


def test_grid_component_create_grid(
    mocker: MockerFixture,
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    model = mock_model("grid")
    mocker.patch.object(model, "region", build_region.to_crs(28992))
    # Set up the component
    component = GridComponent(model=model)
    # Assert current state
    assert "y" not in component.data.dims

    # Call the method
    component.create_grid(res=10)

    # Assert the output
    assert "y" in component.data.dims
    assert component.data.raster.shape == (338, 252)


def test_grid_component_create_grid_like(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model("grid"))

    # Create grid from raster blueprint
    component.create_grid(ds_like=hazard)

    # Assert the output
    assert "y" in component.data.dims
    assert component.data.raster.shape == (35, 27)


def test_grid_component_create_grid_errors(
    mocker: MockerFixture,
    mock_model: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    model = mock_model("grid")
    # Setup the component
    component = GridComponent(model=model)

    # Call with no input
    with pytest.raises(
        ValueError,
        match="Provide either `res` or `ds_like`",
    ):
        component.create_grid()

    mocker.patch.object(model, "region", None)
    # With no region when setting res
    with pytest.raises(
        MissingRegionError,
        match="Region is required for creating grid dimensions",
    ):
        component.create_grid(res=10)

    # Set data like a dummy
    component._data = exposure_grid_clipped

    # Spatial dimensions are there
    with pytest.raises(
        RuntimeError,
        match="GridComponent already contains spatial coordinates",
    ):
        component.create_grid(res=10)


def test_grid_component_reproject(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (35, 27)
    assert component.crs.to_epsg() == 28992
    np.testing.assert_almost_equal(component.data.x.values[0], 85150)

    # Reproject the data
    ds = component.reproject(crs=4326)

    # Assert the output
    assert not component.data.equals(ds)
    assert component.crs.to_epsg() == 28992
    assert ds.raster.crs.to_epsg() == 4326
    assert ds.flood_event.shape == (28, 35)
    np.testing.assert_almost_equal(ds.longitude.values[0], 4.371, decimal=3)


def test_grid_component_reproject_inplace(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (35, 27)
    assert component.crs.to_epsg() == 28992

    # Reproject inplace
    ds = component.reproject(crs=CRS.from_epsg(4326), inplace=True)

    # Assert the output/ state
    assert ds is None
    assert component.crs.to_epsg() == 4326
    assert component.data.flood_event.shape == (28, 35)


def test_grid_component_reproject_nothing(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    id_before = id(component.data)  # To check later

    # Reproject with the same crs
    ds = component.reproject(crs="EPSG:28992")
    # Assert the state/ output
    assert ds is None
    assert id_before == id(component.data)

    # Same yields true when the data crs is None
    component._data = component._data.drop_vars("spatial_ref")
    id_before = id(component.data)  # To check later

    # Reproject with the same crs
    ds = component.reproject(crs="EPSG:4326")
    # Assert the state/ output
    assert ds is None
    assert id_before == id(component.data)


def test_grid_component_set(
    mock_model: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model("grid"))
    # Assert nothing in the component
    assert len(component.data.data_vars) == 0

    # Set the data via the set method, providing a dataset
    component.set(exposure_grid_clipped)

    # Assert the state
    assert len(component.data.data_vars) == 7
    assert "commercial_content" in component.data.data_vars

    # Set data as a dataarray
    component.set(exposure_grid_clipped["commercial_content"], name="foo")

    # Assert the state
    assert len(component.data.data_vars) == 8
    assert "foo" in component.data.data_vars


def test_grid_component_set_replace(
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    caplog.set_level(logging.WARNING)
    # Set up the component
    component = GridComponent(model=mock_model("grid"))
    # Assert nothing in the component
    assert len(component.data.data_vars) == 0

    # Set the data via the set method, providing a dataset
    component.set(exposure_grid_clipped)
    component.set(exposure_grid_clipped)

    # Assert the logging message
    assert "Replacing grid map: 'commercial_content'" in caplog.text

    # Assert the state
    assert len(component.data.data_vars) == 7  # not 14
    assert "commercial_content" in component.data.data_vars


def test_grid_component_set_errors(
    mock_model: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Set up the component
    component = GridComponent(model=mock_model("grid"))

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
