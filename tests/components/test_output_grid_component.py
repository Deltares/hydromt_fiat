from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import xarray as xr
from hydromt.model import ModelRoot

from hydromt_fiat.components import OutputGridComponent


def test_output_grid_component_empty(mock_model: MagicMock):
    # Set up the component
    component = OutputGridComponent(model=mock_model("grid"))

    # Assert the state
    assert component._data is None
    assert isinstance(component.data, xr.Dataset)  # Initialized


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
