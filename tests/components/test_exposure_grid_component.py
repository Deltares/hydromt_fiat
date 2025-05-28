import logging
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
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
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    model_with_region: FIATModel,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = ExposureGridComponent(model=model_with_region)

    # create linking table
    linking_table = pd.DataFrame(
        data=[{"type": "flood_event", "curve_id": "vulnerability_curve"}]
    )
    linking_table_fp = tmp_path / "linking_table.csv"
    linking_table.to_csv(linking_table_fp)

    # Mock vulnerability_data attribute to pass check
    mocker.patch.object(FIATModel, "vulnerability_data")
    component.setup_exposure_grid(
        exposure_grid_fnames=["flood_event"],
        exposure_grid_link_fname=linking_table_fp.as_posix(),
    )
    assert isinstance(component.data, xr.Dataset)
    flood_event_da = component.data.flood_event
    assert flood_event_da.attrs.get("fn_damage") == "vulnerability_curve"
    assert "Setting up exposure grid" in caplog.text
    assert (
        model_with_region.config.get_value("exposure.grid.file") == component._filename
    )

    # Check if config is set properly when data is added to existing grid
    component.setup_exposure_grid(
        exposure_grid_fnames=["flood_event_highres"],
        exposure_grid_link_fname=linking_table_fp.as_posix(),
    )

    assert model_with_region.config.get_value("exposure.grid.settings.var_as_band")


def test_exposure_grid_component_setup_errors(
    tmp_path: Path,
    mocker: MockerFixture,
    model: FIATModel,
    build_region: Path,
):
    # Setup the component
    component = ExposureGridComponent(model=model)

    # Assert the errors pop up
    err_msg = "setup_vulnerability step is required before setting up exposure grid."
    with pytest.raises(RuntimeError, match=err_msg):
        component.setup_exposure_grid(
            exposure_grid_fnames="flood_event",
            exposure_grid_link_fname="test.csv",
        )

    mocker.patch.object(FIATModel, "vulnerability_data")
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid."
    ):
        component.setup_exposure_grid(
            exposure_grid_fnames="flood_event",
            exposure_grid_link_fname="test.csv",
        )

    # check raise value error if linking table does not exist
    model.setup_region(build_region)
    with pytest.raises(ValueError, match="Given path to linking table does not exist."):
        component.setup_exposure_grid(
            exposure_grid_fnames=["flood_event"],
            exposure_grid_link_fname="not/a/file/path",
        )
    linking_table = pd.DataFrame(
        data=[{"exposure": "flood_event", "curve_id": "damage_fn"}]
    )
    linking_table_fp = tmp_path / "test_linking_table.csv"
    linking_table.to_csv(linking_table_fp, index=False)

    with pytest.raises(
        ValueError, match="Missing column, 'type' in exposure grid linking table"
    ):
        component.setup_exposure_grid(
            exposure_grid_fnames=["flood_event"],
            exposure_grid_link_fname=linking_table_fp.as_posix(),
        )

    linking_table = pd.DataFrame(
        data=[{"type": "flood_event", "curve_name": "damage_fn"}]
    )
    linking_table_fp = tmp_path / "test_linking_table.csv"
    linking_table.to_csv(linking_table_fp, index=False)

    with pytest.raises(
        ValueError, match="Missing column, 'curve_id' in exposure grid linking table"
    ):
        component.setup_exposure_grid(
            exposure_grid_fnames=["flood_event"],
            exposure_grid_link_fname=linking_table_fp.as_posix(),
        )
