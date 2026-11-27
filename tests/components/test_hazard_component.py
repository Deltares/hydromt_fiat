import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import numpy as np
import pytest
import xarray as xr
from hydromt.model.mode import ModelMode
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.components import HazardComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.settings.hazard import HazardVariable
from hydromt_fiat.utils import (
    HAZARD,
    RP,
    WATER__DEPTH,
)


def test_hazard_component_empty(
    mock_model: MagicMock,
):
    # Set up the component
    component = HazardComponent(model=mock_model("geom"))

    # Assert some very basic stuff
    assert component._filename == f"{HAZARD}.nc"
    assert component._name == HAZARD
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_hazard_component_read(
    mock_model_read: MagicMock,
):
    # Setup the model
    model = mock_model_read("geom")
    # Setup the component
    component = HazardComponent(model=model)
    # Assert current state
    assert component._data is None

    # Read the data by calling 'data' property
    # This will fall back on the config
    component.data

    # Assert the state
    assert component._data is not None
    assert len(component.data.data_vars) == 1
    # Assert the attributes, which are inferred as there are no settings present
    assert component.data_attrs["flood_event"].type == WATER__DEPTH


def test_hazard_component_read_settings(
    mock_model_read: MagicMock,
):
    # Setup the model with the settings file
    model = mock_model_read("geom", settings="settings_geom.toml")
    # Set a different type in the settings
    model.config.data.hazard.variables[0].type = "duration"
    # Setup the component
    component = HazardComponent(model=model)

    # Read the data by calling 'data' property
    component.data

    # Assert the attributes, which are taken from the settings
    assert component.data_attrs["flood_event"].type == "duration"


def test_hazard_component_read_sig(
    mock_model_read: MagicMock,
):
    # Setup the model
    model = mock_model_read("geom")
    # Setup the component
    component = HazardComponent(model=model)

    # Read data with the 'read' method
    component.read(f"{HAZARD}.nc")

    # Assert the state
    assert len(component.data.data_vars) == 1


def test_hazard_component_read_nothing(
    mocker: MockerFixture,
    mock_model_config: MagicMock,
):
    # Setup the model
    model = mock_model_config("geom")
    mocker.patch.object(
        type(model.root),
        "mode",
        new_callable=PropertyMock,
        return_value=ModelMode("r"),
    )
    # Setup the component
    component = HazardComponent(model=model)
    # Assert current state
    assert len(component.data) == 0

    # Read the data (nothing)
    component.read()
    # Assert still no data
    assert len(component.data) == 0


def test_hazard_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_clipped: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config("geom"))
    # Set data like a dummy
    component._data = hazard_clipped
    component._data_attrs = {}
    component.set_attrs("flood_event", dict(type=WATER__DEPTH))

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, f"{HAZARD}.nc").is_file()

    # Assert the config file
    assert component.model.config.data.hazard.file == Path(tmp_path, f"{HAZARD}.nc")
    variables = component.model.config.data.hazard.variables
    assert len(variables) == 1
    assert variables[0].name == "flood_event"
    assert variables[0].type == WATER__DEPTH


def test_hazard_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    hazard_clipped: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model_config("geom"))
    # Set data like a dummy
    component._data = hazard_clipped
    component._data["flood_event2"] = hazard_clipped["flood_event"]
    component._data_attrs = {}
    component.set_attrs("flood_event", dict(type=WATER__DEPTH))
    component.set_attrs("flood_event2", dict(type=WATER__DEPTH))

    # Write the data using the argument of the read method
    component.write("other/baz.nc")

    # Assert the output
    assert Path(tmp_path, "other", "baz.nc").is_file()

    # Assert the config file
    assert component.model.config.data.hazard.file == Path(tmp_path, "other", "baz.nc")
    assert len(component.model.config.data.hazard.variables) == 2


def test_hazard_component_create(
    caplog: pytest.LogCaptureFixture,
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)
    # Test hazard event
    caplog.set_level(logging.INFO)
    component.create(
        hazard_fname="flood_event",
        hazard_type="water_depth",
        unit="m",
        name="flood_event",
    )

    assert "Processing water_depth hazard data" in caplog.text
    assert "flood_event" in component.data.data_vars
    assert component.data.raster.shape == (7, 6)
    # Assert the attributes
    assert isinstance(component.data_attrs["flood_event"], HazardVariable)
    assert component.data_attrs["flood_event"].type == WATER__DEPTH
    assert component.data_attrs["flood_event"].rp is None


def test_hazard_component_create_multi(
    model_with_region: FIATModel,
):
    # Setup the component
    component = HazardComponent(model=model_with_region)

    # Test setting data to hazard grid with data
    component.create(
        hazard_fname="flood_event",
        hazard_type="water_depth",
        unit="m",
        name="flood_event",
        expand=False,
    )
    component.create(
        hazard_fname="flood_event_highres",
        hazard_type="water_depth",
        unit="m",
        name="flood_event_highres",
        expand=False,
    )

    # Check if both ds are still there
    assert "flood_event" in component.data.data_vars
    assert "flood_event_highres" in component.data.data_vars
    assert set(component.data_attrs) == {"flood_event", "flood_event_highres"}


def test_hazard_component_create_risk(
    model: FIATModel,
):
    model.set_risk(True)
    # Setup the component
    component = HazardComponent(model=model)

    # Test hazard with return period
    component.create(
        hazard_fname="flood_event_highres",
        hazard_type="water_depth",
        unit="m",
        return_period=50000,
        name="flood_event_highres",
        region=False,
    )

    assert isinstance(component.data, xr.Dataset)
    assert component.data.flood_event_highres.attrs[RP] == 50000
    assert model.config.data.risk
    # Assert the attributes
    assert component.data_attrs["flood_event_highres"].rp == 50000


def test_hazard_component_create_region(
    model: FIATModel,
):
    # Setup the component, the model has no region
    component = HazardComponent(model=model)
    assert model.region is None

    # Call the method without the model region
    component.create(
        hazard_fname="flood_event",
        hazard_type="water_depth",
        unit="m",
        name="flood_event",
        region=False,
    )

    # Assert the region is set from the hazard data
    assert model.region is not None
    assert model.region.crs == component.crs
    assert component.data.raster.shape == (51, 33)
    np.testing.assert_array_almost_equal(
        model.region.total_bounds,
        component.bounds,
    )


def test_hazard_component_create_region_present(
    model_with_region: FIATModel,
):
    # Setup the component, the model has a region
    component = HazardComponent(model=model_with_region)
    region = model_with_region.region.copy()

    # Call the method
    component.create(
        hazard_fname="flood_event",
        hazard_type="water_depth",
        unit="m",
        name="flood_event",
        fancy=True,
    )

    # Assert the region and data are untouched by the fancy option
    assert model_with_region.region.equals(region)
    assert component.data.raster.shape == (7, 6)


def test_hazard_component_create_fancy(
    model: FIATModel,
):
    # Setup the component, the model has no region
    component = HazardComponent(model=model)

    # Call the method, vectorizing the data for the region
    component.create(
        hazard_fname="flood_event",
        hazard_type="water_depth",
        unit="m",
        name="flood_event",
        region=False,
        fancy=True,
    )

    # Assert the region is set and the data is clipped on it
    assert model.region is not None
    assert model.region.crs == component.crs
    assert "flood_event" in component.data.data_vars
    assert component.data.raster.shape == (46, 33)
    # The region is smaller than the bounds of the original data
    assert model.region.area.sum() < 3300 * 5100


def test_hazard_component_create_errors(model: FIATModel):
    # Setup the component
    component = HazardComponent(model=model)

    # Set risk
    model.config.data.risk = True

    # Assert the errors
    with pytest.raises(
        ValueError, match="Cannot perform risk analysis without a return period"
    ):
        component.create(
            hazard_fname="test.nc",
            hazard_type="water_depth",
            unit="m",
        )

    # Set risk
    model.config.data.risk = False

    # Provide a return period without settings the model to risk
    with pytest.raises(
        ValueError, match="Return period is set while the model is not set to risk mode"
    ):
        component.create(
            hazard_fname="test.nc",
            hazard_type="water_depth",
            unit="m",
            return_period=10,
        )

    # No region provided
    with pytest.raises(
        MissingRegionError,
        match="Model region is missing for setting up hazard data",
    ):
        component.create(
            hazard_fname="flood_event",
            hazard_type="water_depth",
            unit="m",
        )


def test_hazard_component_create_fixed(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model("geom"))
    # Set data like a dummy
    component._data = hazard
    component._data_attrs = {}

    # Call the method
    component.create_fixed(
        "flood_event",
        "water_depth",
        "flood_fixed",
        value=1,
    )

    # Assert the output, the fixed layer is added next to the original
    assert "flood_event" in component.data.data_vars
    assert "flood_fixed" in component.data.data_vars
    finite = component.data["flood_event"].values != -9999
    assert (component.data["flood_fixed"].values[finite] == 1).all()
    assert (component.data["flood_fixed"].values[~finite] == -9999).all()
    # Assert the attributes
    assert isinstance(component.data_attrs["flood_fixed"], HazardVariable)
    assert component.data_attrs["flood_fixed"].type == WATER__DEPTH
    assert component.data_attrs["flood_fixed"].rp is None


def test_hazard_component_create_fixed_risk(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model("geom"))
    # Set data like a dummy
    component._data = hazard
    component._data_attrs = {}

    # Call the method with a return period and hazard type
    component.create_fixed(
        "flood_event",
        hazard_type="flooding",
        name="flood_fixed",
        value=1,
        return_period=100,
    )

    # Assert the attributes
    assert component.data_attrs["flood_fixed"].type == "flooding"
    assert component.data_attrs["flood_fixed"].rp == 100


def test_hazard_component_create_fixed_errors(
    mock_model: MagicMock,
    hazard: xr.Dataset,
):
    # Setup the component
    component = HazardComponent(model=mock_model("geom"))
    # Set data like a dummy
    component._data = hazard
    component._data_attrs = {}

    # Hazard layer not present
    with pytest.raises(
        RuntimeError,
        match="Choose from already present data variables",
    ):
        component.create_fixed("foo", "water_depth", "flood_fixed", value=1)


def test_hazard_component_create_settings_only(
    mock_model: MagicMock,
):
    # Setup the component
    component = HazardComponent(model=mock_model("geom"))

    # Call the method
    component.create_settings_only(
        "water_depth",
        "flood_const",
        value=0.5,
    )

    # Assert the output, there is only an entry in the attributes
    assert len(component.data.data_vars) == 0
    assert isinstance(component.data_attrs["flood_const"], HazardVariable)
    assert component.data_attrs["flood_const"].type == WATER__DEPTH
    assert component.data_attrs["flood_const"].rp is None
    assert component.data_attrs["flood_const"].value == 0.5


def test_hazard_component_create_settings_only_risk(
    mock_model: MagicMock,
):
    # Setup the component
    component = HazardComponent(model=mock_model("geom"))

    # Call the method with a return period and hazard type
    component.create_settings_only(
        hazard_type="flooding",
        name="flood_const",
        value=0.5,
        return_period=100,
    )

    # Assert the attributes
    assert component.data_attrs["flood_const"].type == "flooding"
    assert component.data_attrs["flood_const"].rp == 100
