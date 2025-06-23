import logging
from unittest.mock import MagicMock

import pytest
import xarray as xr
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


def test_exposure_grid_component_setup(
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    model_with_region: FIATModel,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = ExposureGridComponent(model=model_with_region)

    # Mock vulnerability_data attribute to pass check
    mocker.patch.object(FIATModel, "vulnerability_data")
    # Call the method
    component.setup_exposure_grid(
        exposure_fnames="industrial_content",
        exposure_link_fname="exposure_grid_link",
    )

    # Assert the output
    assert isinstance(component.data, xr.Dataset)
    assert "Setting up exposure grid" in caplog.text
    assert (
        model_with_region.config.get_value("exposure.grid.file") == component._filename
    )
    assert "industrial_content" in component.data.data_vars


def test_exposure_grid_component_setup_multi(
    mocker: MockerFixture,
    model_with_region: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model_with_region)

    # Mock vulnerability_data attribute to pass check
    mocker.patch.object(FIATModel, "vulnerability_data")
    # Call the method
    component.setup_exposure_grid(
        exposure_fnames=["industrial_content", "industrial_structure"],
        exposure_link_fname="exposure_grid_link",
    )

    # Assert the output
    assert "industrial_content" in component.data.data_vars
    assert "industrial_structure" in component.data.data_vars
    assert component.data.industrial_structure.attrs.get("fn_damage") == "in2"


def test_exposure_grid_component_setup_errors(
    mocker: MockerFixture,
    model: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model)

    # Assert the vulnerability absent error
    err_msg = "setup_vulnerability step is required before setting up exposure grid."
    with pytest.raises(RuntimeError, match=err_msg):
        component.setup_exposure_grid(
            exposure_fnames="industrial_content",
            exposure_link_fname="",  # Can be nonsense, error is raised earlier
        )

    # Assert missing region error
    mocker.patch.object(FIATModel, "vulnerability_data")
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid."
    ):
        component.setup_exposure_grid(
            exposure_fnames="industrial_content",
            exposure_link_fname="",
        )
