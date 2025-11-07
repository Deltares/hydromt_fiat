import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import pytest
import xarray as xr
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import HazardComponent
from hydromt_fiat.errors import MissingRegionError


def test_hazard_component_empty(
    mock_model: MagicMock,
):
    # Set up the component
    component = HazardComponent(model=mock_model)

    # Assert some very basic stuff
    assert component._filename == "hazard.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_hazard_component_clear(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Set up the component
    component = HazardComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert len(component.data.data_vars) == 1

    # Call the clear method
    component.clear()
    # Assert the state after
    assert len(component.data.data_vars) == 0


def test_hazard_component_clip(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    hazard: xr.Dataset,
):
    # Set up the component
    component = HazardComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (34, 25)

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small)
    # Assert the output
    assert ds.flood_event.shape == (5, 4)


def test_hazard_component_clip_no_data(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
):
    # Set up the component
    component = HazardComponent(model=mock_model)
    # Assert the current state
    assert component._data is None

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small)
    # Assert that there is no output
    assert ds is None


def test_hazard_component_clip_inplace(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    hazard: xr.Dataset,
):
    # Set up the component
    component = HazardComponent(model=mock_model)

    # Set data like a dummy
    component._data = hazard
    # Assert the current state
    assert component.data.flood_event.shape == (34, 25)

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small, inplace=True)
    # Assert that the output is None but the shape of the component data changed
    assert ds is None
    assert component.data.flood_event.shape == (5, 4)


def test_hazard_component_read(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Assert current state
    assert component._data is None

    # Read the data by calling 'data' property
    # This will fall back on the config
    component.data

    # Assert the state
    assert component._data is not None
    assert len(component.data.data_vars) == 1


def test_hazard_component_read_sig(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = HazardComponent(model=mock_model_config)

    # Read data with the 'read' method
    component.read("hazard.nc")

    # Assert the state
    assert len(component.data.data_vars) == 1


def test_hazard_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_clipped: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Set data like a dummy
    component._data = hazard_clipped

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, "hazard.nc").is_file()

    # Assert the config file
    assert component.model.config.get("hazard.file") == Path(tmp_path, "hazard.nc")
    assert not component.model.config.get("hazard.settings.var_as_band")


def test_hazard_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_clipped: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config)
    # Set data like a dummy
    component._data = hazard_clipped
    component._data["flood_event2"] = hazard_clipped["flood_event"]

    # Write the data using the argument of the read method
    component.write("other/baz.nc")

    # Assert the output
    assert Path(tmp_path, "other", "baz.nc").is_file()

    # Assert the config file
    assert component.model.config.get("hazard.file") == Path(
        tmp_path, "other", "baz.nc"
    )
    assert component.model.config.get("hazard.settings.var_as_band")


def test_hazard_component_setup_event(
    caplog: pytest.LogCaptureFixture,
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)
    # Test hazard event
    caplog.set_level(logging.INFO)
    component.setup(hazard_fnames="flood_event", elevation_reference="dem")

    assert "Added water_depth hazard map: flood_event" in caplog.text
    assert model_with_region.config.get("hazard.elevation_reference") == "dem"


def test_hazard_component_setup_multi(
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)

    # Test setting data to hazard grid with data
    component.setup(hazard_fnames=["flood_event", "flood_event_highres"])

    # Check if both ds are still there
    assert "flood_event" in component.data.data_vars.keys()
    assert "flood_event_highres" in component.data.data_vars.keys()


def test_hazard_component_setup_risk(
    model_with_region: FIATModel,
):
    # Setup the compoentn
    component = HazardComponent(model=model_with_region)

    # Test hazard with return period
    component.setup(
        hazard_fnames=["flood_event_highres"],
        risk=True,
        return_periods=[50000],
    )

    assert isinstance(component.data, xr.Dataset)
    assert model_with_region.config.get("model.risk")
    assert model_with_region.config.get("hazard.return_periods") == [50000]


def test_hazard_component_setup_errors(model: FIATModel):
    # Setup the component
    component = HazardComponent(model=model)

    # Assert the errors
    with pytest.raises(
        ValueError, match="Cannot perform risk analysis without return periods"
    ):
        component.setup(hazard_fnames="test.nc", risk=True)

    with pytest.raises(
        ValueError, match="Return periods do not match the number of hazard files"
    ):
        component.setup(
            hazard_fnames=["test1.nc", "test2.nc"],
            risk=True,
            return_periods=[1, 2, 3],
        )

    with pytest.raises(
        MissingRegionError,
        match=("Region component is missing for setting up hazard data."),
    ):
        component.setup(hazard_fnames=["flood_event"])
