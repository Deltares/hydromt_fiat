from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pandas as pd
import pytest
import xarray as xr
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ExposureGridComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.utils import (
    EXPOSURE,
    EXPOSURE_GRID_FILE,
    EXPOSURE_GRID_SETTINGS,
    FN_CURVE,
    GRID,
    MODEL_TYPE,
    VAR_AS_BAND,
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
    tmp_path: Path,
    mock_model_config: MagicMock,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="r"),
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
    assert component.model.config.get(EXPOSURE_GRID_FILE) == Path(
        tmp_path,
        EXPOSURE,
        "spatial.nc",
    )
    assert component.model.config.get(f"{EXPOSURE_GRID_SETTINGS}.{VAR_AS_BAND}")


def test_exposure_grid_component_write_config(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config)

    # Set data like a dummy
    component._data = exposure_grid_clipped["industrial_content"].to_dataset()
    # Add to the config
    component.model.config.set(EXPOSURE_GRID_FILE, "foo.nc")

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, "foo.nc").is_file()
    # Assert the config
    assert not component.model.config.get(f"{EXPOSURE_GRID_SETTINGS}.{VAR_AS_BAND}")


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
    assert component.model.config.get(EXPOSURE_GRID_FILE) == Path(
        tmp_path,
        "baz.nc",
    )


def test_exposure_grid_component_setup(
    model_exposure_setup: FIATModel,
    vulnerability_identifiers_path: Path,
):
    component = ExposureGridComponent(model=model_exposure_setup)

    component.setup(
        exposure_fnames="industrial_content",
        vulnerability_link_fname=vulnerability_identifiers_path,
    )

    assert isinstance(component.data, xr.Dataset)
    assert "industrial_content" in component.data.data_vars
    assert component.data.industrial_content.attrs.get(FN_CURVE) == "in2"
    assert component.data.raster.shape == (11, 11)

    assert component.model.config.get(MODEL_TYPE) == GRID
    assert not component.model.config.get(f"{EXPOSURE_GRID_SETTINGS}.{VAR_AS_BAND}")


def test_exposure_grid_component_setup_multi(
    model_exposure_setup: FIATModel,
    vulnerability_identifiers_path: Path,
):
    component = ExposureGridComponent(model=model_exposure_setup)

    component.setup(
        exposure_fnames=["industrial_content", "industrial_structure"],
        exposure_link_fname="exposure_grid_link",
        vulnerability_link_fname=vulnerability_identifiers_path,
        expand=False,
    )

    assert "industrial_content" in component.data.data_vars
    assert "industrial_structure" in component.data.data_vars
    assert component.data.industrial_structure.attrs.get(FN_CURVE) == "in1"


def test_exposure_grid_component_setup_errors(
    model: FIATModel,
    vulnerability_curves: pd.DataFrame,
    vulnerability_identifiers_path: Path,
):
    component = ExposureGridComponent(model=model)

    # Assert the vulnerability absent error
    with pytest.raises(RuntimeError, match="No vulnerability curves"):
        component.setup(
            exposure_fnames="industrial_content",
            vulnerability_link_fname=vulnerability_identifiers_path,
            exposure_link_fname="",  # nonsense; error is raised earlier
        )

    # Set curves so the first check passes, then assert missing-region error
    model.vulnerability._set_curves(vulnerability_curves)
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid"
    ):
        component.setup(
            exposure_fnames="industrial_content",
            vulnerability_link_fname=vulnerability_identifiers_path,
            exposure_link_fname="",
        )
