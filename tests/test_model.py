import logging

import pytest
from hydromt import DataCatalog

from hydromt_fiat import FIATModel


def test_empty_model(tmp_path):
    # Setup an empty fiat model
    model = FIATModel(tmp_path)

    # Assert some basic statements
    assert "config" in model.components
    assert "region" in model.components
    assert model.region is None
    assert len(model.components) == 7


def test_basic_read_write(tmp_path, build_region):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Call the necessary setup methods
    model.setup_config(model="geom")
    model.setup_region(region=build_region)
    # Write the model
    model.write()
    model = None

    # Model in read mode
    model = FIATModel(tmp_path, mode="r")
    model.read()

    assert model.region is not None


def test_setup_hazard(tmp_path, build_data_catalog, caplog):
    # Setup the model
    model = FIATModel(tmp_path, data_libs=[build_data_catalog])

    with pytest.raises(
        ValueError, match="Cannot perform risk analysis without return periods"
    ):
        model.setup_hazard(hazard_fnames="test.nc", risk=True)

    with pytest.raises(
        ValueError, match="Return periods do not match the number of hazard files"
    ):
        model.setup_hazard(
            hazard_fnames=["test1.nc", "test2.nc"],
            risk=True,
            return_periods=[1, 2, 3],
        )

    # Test hazard event
    caplog.set_level(logging.INFO)
    dc = DataCatalog(build_data_catalog)
    hazard_source = dc.get_source("flood_event")
    model.setup_hazard(hazard_fnames=hazard_source.full_uri)
    assert "Added flooding hazard map: event" in caplog.text
    raster = dc.get_rasterdataset("flood_event")
    grid_component = model.get_component("hazard_grid")
    assert raster.shape == grid_component.data.event.shape
    assert grid_component.data.event.name == "event"
    assert grid_component.data.event.type == "flooding"
    assert grid_component.data.event.analysis == "event"
    assert model.config.get_value("hazard.file") == "hazard_grid.nc"
    assert model.config.get_value("hazard.elevation_reference") == "datum"

    # Test setting data to hazard grid with data
    with pytest.raises(
        ValueError, match="Cannot set hazard data on existing hazard grid data."
    ):
        model.setup_hazard(hazard_fnames="flood_event")

    # Test hazard with return period
    model2 = FIATModel(tmp_path, data_libs=[build_data_catalog])

    fnames = ["flood_50000"]
    model2.setup_hazard(hazard_fnames=fnames, risk=True, return_periods=[50000])
    grid_component2 = model2.get_component("hazard_grid")
    assert grid_component2.data.analysis == "risk"
    assert grid_component2.data.name == ["flood_50000"]
    assert grid_component2.data.return_period == [50000]
    assert model2.config.get_value("hazard.risk")
    assert model2.config.get_value("hazard.return_periods") == [50000]
