from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
import xarray as xr
from hydromt.model import ModelRoot
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ExposureGridComponent
from hydromt_fiat.errors import MissingRegionError


def test_exposure_grid_component_empty(
    mock_model: MagicMock,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model)

    # Assert some basics
    assert component._filename == "exposure/spatial.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_exposure_grid_component_read(
    mock_model_config: MagicMock,
    model_cached: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Read the data by calling the data property
    component.data

    # No config so it wont read anything
    assert len(component.data.data_vars) == 4
    assert "industrial_content" in component.data.data_vars


def test_exposure_grid_component_read_sig(
    mock_model_config: MagicMock,
    model_cached: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Read the data using the signature of the read method
    component.read("exposure/spatial.nc")

    # No config so it wont read anything
    assert len(component.data.data_vars) == 4
    assert "industrial_content" in component.data.data_vars


def test_exposure_grid_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_grid_data: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Set data like a dummy
    component._data = exposure_grid_data

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, "exposure", "spatial.nc").is_file()
    # Assert the config
    assert component.model.config.get("exposure.grid.file") == Path(
        tmp_path,
        "exposure",
        "spatial.nc",
    )
    assert component.model.config.get("exposure.grid.settings.var_as_band")


def test_exposure_grid_component_write_config(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_grid_data: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Set data like a dummy
    component._data = exposure_grid_data["industrial_content"].to_dataset()
    # Add to the config
    component.model.config.set("exposure.grid.file", "foo.nc")

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, "foo.nc").is_file()
    # Assert the config
    assert not component.model.config.get("exposure.grid.settings.var_as_band")


def test_exposure_grid_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_grid_data: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Set data like a dummy
    component._data = exposure_grid_data

    # Write the data
    component.write("baz.nc")

    # Assert the output
    assert Path(tmp_path, "baz.nc").is_file()
    # Assert the config file
    assert component.model.config.get("exposure.grid.file") == Path(
        tmp_path,
        "baz.nc",
    )


def test_exposure_grid_component_setup(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup)

    # Call the method
    component.setup(
        exposure_fnames="industrial_content",
    )

    # Assert the output
    assert isinstance(component.data, xr.Dataset)
    assert "industrial_content" in component.data.data_vars

    # Assert entries in the config
    assert component.model.config.get("model.model_type") == "grid"
    assert not component.model.config.get("exposure.grid.settings.var_as_band")


def test_exposure_grid_component_setup_multi(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup)

    # Call the method
    component.setup(
        exposure_fnames=["industrial_content", "industrial_structure"],
        exposure_link_fname="exposure_grid_link",
    )

    # Assert the output
    assert "industrial_content" in component.data.data_vars
    assert "industrial_structure" in component.data.data_vars
    assert component.data.industrial_structure.attrs.get("fn_damage") == "in1"


def test_exposure_grid_component_setup_errors(
    mocker: MockerFixture,
    model: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model)

    # Assert the vulnerability absent error
    err_msg = "'setup_vulnerability' step is required before setting up exposure grid"
    with pytest.raises(RuntimeError, match=err_msg):
        component.setup(
            exposure_fnames="industrial_content",
            exposure_link_fname="",  # Can be nonsense, error is raised earlier
        )

    # Assert missing region error
    mocker.patch.object(FIATModel, "vulnerability")
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid"
    ):
        component.setup(
            exposure_fnames="industrial_content",
            exposure_link_fname="",
        )
