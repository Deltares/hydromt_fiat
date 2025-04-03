import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import xarray as xr

from hydromt_fiat import FIATModel
from hydromt_fiat.errors import MissingRegionError


def test_empty_model(tmp_path):
    # Setup an empty fiat model
    model = FIATModel(tmp_path)

    # Assert some basic statements
    assert "config" in model.components
    assert "region" in model.components
    assert model.region is None
    assert len(model.components) == 7


def test_basic_read_write(tmp_path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Call the necessary setup methods
    model.setup_config(some_var="some_value")
    # Write the model
    model.write()
    model = None
    assert Path(tmp_path, "settings.toml").is_file()

    # Model in read mode
    model = FIATModel(tmp_path, mode="r")
    model.read()

    assert len(model.config.data) != 0


def test_setup_config(tmp_path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Setup some config variables
    model.setup_config(
        **{
            "global.model": "geom",
            "global.srs.value": "EPSG:4326",
            "output.path": "output",
        }
    )

    # Assert the config component
    assert model.config.data["output"] == {"path": "output"}
    assert model.config.get_value("output.path") == "output"
    assert len(model.config.get_value("global")) == 2
    assert model.config.get_value("global.srs") == {"value": "EPSG:4326"}


def test_setup_region(tmp_path, build_region):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")
    assert model.region is None

    # Setup the region
    model.setup_region(region=build_region)
    assert model.region is not None
    assert isinstance(model.region, gpd.GeoDataFrame)
    assert len(model.region) == 1


def test_setup_region_error(tmp_path):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Setup the region
    region_no = Path(tmp_path, "region.geojson")
    with pytest.raises(FileNotFoundError, match=region_no.as_posix()):
        model.setup_region(region=region_no)


def test_setup_vulnerability(tmp_path, build_data_catalog):
    # Setup the model
    model = FIATModel(tmp_path, mode="w+", data_libs=build_data_catalog)

    assert len(model.vulnerability_data.data) == 0

    # Setup the vulnerability
    model.setup_vulnerability(
        vulnerability_fname="jrc_vulnerability_curves",
        vulnerability_linking_fname="jrc_vulnerability_curves_linking",
        continent="europe",
    )

    assert len(model.vulnerability_data.data) == 2
    assert "vulnerability_curves" in model.vulnerability_data.data
    assert "vulnerability_identifiers" in model.vulnerability_data.data
    assert (
        model.config.get_value("vulnerability.file")
        == "vulnerability/vulnerability_curves.csv"
    )


def test_setup_hazard(model, tmp_path, build_data_catalog, caplog, build_region):
    # Setup the model
    model.setup_region(region=build_region)
    # Test hazard event
    caplog.set_level(logging.INFO)
    model.setup_hazard(hazard_fnames="flood_event")

    assert "Added flooding hazard map: flood_event" in caplog.text
    assert model.config.get_value("hazard.file") == "hazard/hazard_grid.nc"
    assert model.config.get_value("hazard.elevation_reference") == "datum"

    # Test setting data to hazard grid with data
    model.setup_hazard(hazard_fnames="flood_event_highres")
    assert model.config.get_value("hazard.settings.var_as_band")

    # Check if both ds are still there
    assert "flood_event" in model.hazard_grid.data.data_vars.keys()
    assert "flood_event_highres" in model.hazard_grid.data.data_vars.keys()

    # Test hazard with return period
    model2 = FIATModel(tmp_path, data_libs=[build_data_catalog])
    model2.setup_region(region=build_region)
    model2.setup_hazard(
        hazard_fnames=["flood_event_highres"],
        risk=True,
        return_periods=[50000],
    )

    assert isinstance(model2.hazard_grid.data, xr.Dataset)
    assert model2.config.get_value("hazard.risk")
    assert model2.config.get_value("hazard.return_periods") == [50000]


def test_setup_hazard_errors(model):
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

    with pytest.raises(
        MissingRegionError,
        match=("Region component is missing for setting up hazard data."),
    ):
        model.setup_hazard(hazard_fnames=["flood_event"])


def test_setup_exposure_grid(model, build_region, caplog, tmp_path, mocker):
    model.setup_region(region=build_region)

    # create linking table
    linking_table = pd.DataFrame(
        data=[{"type": "flood_event", "curve_id": "vulnerability_curve"}]
    )
    linking_table_fp = tmp_path / "linking_table.csv"
    linking_table.to_csv(linking_table_fp)

    # Mock vulnerability_data attribute to pass check
    mocker.patch.object(FIATModel, "vulnerability_data")
    caplog.set_level(logging.INFO)
    model.setup_exposure_grid(
        exposure_grid_fnames=["flood_event"],
        exposure_grid_link_fname=linking_table_fp.as_posix(),
    )
    assert isinstance(model.exposure_grid.data, xr.Dataset)
    assert model.exposure_grid.data.attrs.get("fn_damage") == "vulnerability_curve"
    assert "Setting up exposure grid" in caplog.text
    assert model.config.get_value("exposure.grid.file") == model.exposure_grid._filename

    # Check if config is set properly when data is added to existing grid
    model.setup_exposure_grid(
        exposure_grid_fnames=["flood_event_highres"],
        exposure_grid_link_fname=linking_table_fp.as_posix(),
    )

    assert model.config.get_value("exposure.grid.settings.var_as_band")


def test_setup_exposure_grid_errors(model, build_region, mocker, tmp_path):
    err_msg = "setup_vulnerability step is required before setting up exposure grid."
    with pytest.raises(RuntimeError, match=err_msg):
        model.setup_exposure_grid(
            exposure_grid_fnames="flood_event",
            exposure_grid_link_fname="test.csv",
        )

    mocker.patch.object(FIATModel, "vulnerability_data")
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid."
    ):
        model.setup_exposure_grid(
            exposure_grid_fnames="flood_event",
            exposure_grid_link_fname="test.csv",
        )

    # check raise value error if linking table does not exist
    model.setup_region(build_region)
    with pytest.raises(ValueError, match="Given path to linking table does not exist."):
        model.setup_exposure_grid(
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
        model.setup_exposure_grid(
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
        model.setup_exposure_grid(
            exposure_grid_fnames=["flood_event"],
            exposure_grid_link_fname=linking_table_fp.as_posix(),
        )
