from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
import xarray as xr
from hydromt.model import ModelRoot
from hydromt.model.mode import ModelMode
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ExposureGridComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.utils import (
    EXPOSURE,
    FN_CURVE,
    GRID,
    VULNERABILITY,
)


def test_exposure_grid_component_empty(
    mock_model: MagicMock,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model)

    # Assert some basics
    assert component._filename == f"{EXPOSURE}/spatial.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_exposure_grid_component_read(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
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
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Read the data using the signature of the read method
    component.read(f"{EXPOSURE}/spatial.nc")

    # No config so it wont read anything
    assert len(component.data.data_vars) == 4
    assert "industrial_content" in component.data.data_vars


def test_exposure_grid_component_read_nothing(
    mocker: MockerFixture,
    mock_model_config: MagicMock,
):
    mocker.patch.object(
        type(mock_model_config.root),
        "mode",
        new_callable=PropertyMock,
        return_value=ModelMode("r"),
    )
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)
    # Assert current state
    assert len(component.data) == 0

    # Read the data (nothing)
    component.read()
    # Assert still no data
    assert len(component.data) == 0


def test_exposure_grid_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Set data like a dummy
    component._data = exposure_grid_clipped

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, EXPOSURE, "spatial.nc").is_file()
    # Assert the config
    assert component.model.config.data.exposure.grid.file == Path(
        tmp_path,
        EXPOSURE,
        "spatial.nc",
    )


def test_exposure_grid_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Set data like a dummy
    component._data = exposure_grid_clipped

    # Write the data
    component.write("baz.nc")

    # Assert the output
    assert Path(tmp_path, "baz.nc").is_file()
    # Assert the config file
    assert component.model.config.data.exposure.grid.file == Path(
        tmp_path,
        "baz.nc",
    )


def test_exposure_grid_component_create(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup)

    # Call the method
    component.create(
        exposure_fnames="industrial_content",
    )

    # Assert the output
    assert isinstance(component.data, xr.Dataset)
    assert "industrial_content" in component.data.data_vars
    assert component.data.industrial_content.attrs.get(FN_CURVE) == "in2"
    assert component.data.raster.shape == (11, 11)

    # Assert entries in the config
    assert component.model.config.data.model.type == GRID


def test_exposure_grid_component_create_multi(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup)

    # Call the method
    component.create(
        exposure_fnames=["industrial_content", "industrial_structure"],
        exposure_link_fname="exposure_grid_link",
        expand=False,
    )

    # Assert the output
    assert "industrial_content" in component.data.data_vars
    assert "industrial_structure" in component.data.data_vars
    assert component.data.industrial_structure.attrs.get(FN_CURVE) == "in1"


def test_exposure_grid_component_create_errors(
    mocker: MockerFixture,
    model: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model)

    # Assert the vulnerability absent error
    err_msg = "'vulnerability.create' step is required before setting up exposure grid"
    with pytest.raises(RuntimeError, match=err_msg):
        component.create(
            exposure_fnames="industrial_content",
            exposure_link_fname="",  # Can be nonsense, error is raised earlier
        )

    # Fake component
    fake_component = mocker.Mock()
    fake_component.data.identifiers.empty = False

    # Assert missing region error
    mocker.patch.object(FIATModel, VULNERABILITY, fake_component)
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid"
    ):
        component.create(
            exposure_fnames="industrial_content",
            exposure_link_fname="",
        )
