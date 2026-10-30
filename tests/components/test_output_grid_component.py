import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
import xarray as xr
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import OutputGridComponent


def test_output_grid_component_empty(mock_model: MagicMock):
    # Set up the component
    component = OutputGridComponent(model=mock_model("grid"))

    # Assert the state
    assert component._data is None
    assert component._processed_data is None
    assert isinstance(component.data, xr.Dataset)  # Initialized
    assert isinstance(component.processed_data, dict)  # Initialized


def test_output_grid_component__set(
    mock_model: MagicMock,
    hazard_clipped: xr.Dataset,
):
    # Setup the component
    component = OutputGridComponent(model=mock_model("grid"))
    assert len(component.processed_data) == 0  # No data yet

    # Set the data (post processed apparently)
    component._set(data=hazard_clipped, name="foo")

    # Assert state
    assert "foo" in component.processed_data
    assert isinstance(component.processed_data["foo"], xr.Dataset)


def test_output_grid_component__set_warnings(
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
    hazard_clipped: xr.Dataset,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = OutputGridComponent(model=mock_model("grid"))
    assert len(component.processed_data) == 0  # No data yet

    # Set data like a dummy
    component._data = {"foo": hazard_clipped}

    # Set the exact same
    component._set(data=hazard_clipped, name="foo")
    # Nothing
    assert "Replacing post processed grid data" not in caplog.text

    # Set a copy
    component._set(data=hazard_clipped.copy(), name="foo")
    # Nothing
    assert "Replacing post processed grid data" in caplog.text


def test_output_grid_component_read_none(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    # Setup the model
    model = mock_model_config("grid")
    type(model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Set up the component
    component = OutputGridComponent(model=model)

    # Assert the state
    assert len(component.data.data_vars) == 0

    # Read (nothing)
    component.read()

    # Assert the state after
    assert len(component.data.data_vars) == 0


def test_output_grid_component_read_not_found(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    # Setup the model
    model = mock_model_config("grid")
    type(model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Set up the component
    component = OutputGridComponent(model=model)

    # Assert the state
    assert len(component.data.data_vars) == 0

    # Read (nothing)
    component.read(filename="spatial.nc")

    # Assert the state after
    assert len(component.data.data_vars) == 0


def test_output_grid_component_read_sig(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    # Setup the model
    model = mock_model_config("grid")
    type(model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Set up the component
    component = OutputGridComponent(model=model)

    # Assert the state
    assert len(component.data.data_vars) == 0

    # Read (nothing)
    component.read(Path(model_data_clipped_path, "exposure", "spatial.nc"))

    # Assert the state after
    assert len(component.data.data_vars) == 7
    assert "commercial_structure" in component.data.data_vars
    assert component.data["commercial_structure"].shape == (11, 11)


def test_output_grid_component_spatial_aggregate(
    model_with_region: FIATModel,
    hazard: xr.Dataset,
):
    # Set up the component
    model_with_region._type = "grid"
    component = OutputGridComponent(model=model_with_region)
    # Set data like a dummy
    component._data = hazard

    # Call the method
    component.spatial_aggregate(
        output_name="flood_event",
        res=500,
        name="foo",
    )

    # Assert the output
    assert "foo" in component.processed_data
    assert isinstance(component.processed_data["foo"], xr.DataArray)
