import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import numpy as np
import pytest
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ExposureGeomsComponent
from hydromt_fiat.errors import MissingRegionError


def test_exposure_geom_component_empty(mock_model: MagicMock):
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)

    # Assert some basics
    assert component._filename == "exposure/{name}.fgb"
    assert len(component.data) == 0
    assert isinstance(component.data, dict)


def test_exposure_geoms_component_clear(
    mock_model: MagicMock,
    exposure_vector: gpd.GeoDataFrame,
):
    # Set up the component
    component = ExposureGeomsComponent(model=mock_model)

    # Set data like a dummy
    component._data = {"foo": exposure_vector}
    # Assert the current state, i.e. amount of rows
    assert len(component.data) == 1

    # Call the clear method
    component.clear()
    # Assert the state after
    assert len(component.data) == 0


def test_exposure_geoms_component_clip(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    exposure_vector: gpd.GeoDataFrame,
):
    # Set up the component
    component = ExposureGeomsComponent(model=mock_model)

    # Set data like a dummy
    component._data = {"foo": exposure_vector}
    # Assert the current state, i.e. amount of rows
    assert component.data["foo"].shape[0] == 543

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small.to_crs(4326))
    # Assert the output
    assert ds["foo"].shape[0] == 12


def test_exposure_geoms_component_clip_no_data(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
):
    # Set up the component
    component = ExposureGeomsComponent(model=mock_model)
    # Assert the current state
    assert component._data is None

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small)
    # Assert that there is no output
    assert ds is None


def test_exposure_geoms_component_clip_inplace(
    mock_model: MagicMock,
    build_region_small: gpd.GeoDataFrame,
    exposure_vector: gpd.GeoDataFrame,
):
    # Set up the component
    component = ExposureGeomsComponent(model=mock_model)

    # Set data like a dummy
    component._data = {"foo": exposure_vector}
    # Assert the current state
    assert component.data["foo"].shape[0] == 543

    # Call the clipping method using a smaller region
    ds = component.clip(geom=build_region_small.to_crs(4326), inplace=True)
    # Assert that the output is None but the shape of the component data changed
    assert ds is None
    assert component.data["foo"].shape[0] == 12


def test_exposure_geom_component_set(
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)
    assert len(component.data) == 0  # No data yet

    # Add a geometry dataset
    component.set(geom=build_region, name="ds1")

    # Assert that it's there
    assert len(component.data) == 1
    assert "ds1" in component.data

    # Overwrite with the same dataset, should produce no warning
    component.set(geom=build_region, name="ds1")
    assert "Replacing geom: ds1" not in caplog.text

    # Overwrite, but with a copy, should produce a warning
    component.set(geom=build_region.copy(), name="ds1")
    assert "Replacing geom: ds1" in caplog.text


def test_exposure_geom_component_region(
    build_region: gpd.GeoDataFrame,
    box_geometry: gpd.GeoDataFrame,
    mock_model: MagicMock,
):
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)
    assert component.region is None

    # Set a second dataset
    component.set(geom=build_region, name="ds1")

    # Assert the content
    assert component.region is not None
    np.testing.assert_array_almost_equal(
        component.region.total_bounds,
        [4.371, 51.966, 4.408, 51.997],
        decimal=3,
    )

    # Add a second geometry to lying completely outside of the first one
    component.set(geom=box_geometry, name="ds2")

    # Assert the region is larger now, eye test
    np.testing.assert_array_almost_equal(
        component.region.total_bounds,
        [4.355, 51.966, 4.408, 52.045],
        decimal=3,
    )


def test_exposure_geom_component_read(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model_config)

    # Assert it's empty
    assert component._data is None

    # Reading by calling the data
    component.data

    # Assert that the data is a dictionary with two elements
    assert isinstance(component._data, dict)
    assert len(component._data) == 1
    assert "buildings" in component.data


def test_exposure_geom_component_read_sig(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model_config)

    # Assert it's empty
    assert component._data is None

    # Calling read to read in the data
    component.read("exposure/{name}.fgb")

    # Assert the output
    assert len(component._data) == 2


def test_exposure_geom_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model_config)
    # Set data like a dummy
    component._data = {
        "buildings": exposure_vector_clipped,
        "buildings2": exposure_vector_clipped,
    }

    # Write the data
    component.write()

    # Assert the files
    assert Path(tmp_path, component._filename.format(name="buildings")).is_file()
    assert Path(tmp_path, component._filename.format(name="buildings2")).is_file()

    # Assert the config file entries
    geom_cfg = mock_model_config.config.get("exposure.geom")
    assert len(geom_cfg) == 2
    assert geom_cfg[0]["file"] == Path(tmp_path, "exposure/buildings.fgb")


def test_exposure_geom_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model_config)
    # Set data like a dummy
    component._data = {
        "buildings": exposure_vector_clipped,
    }

    # Write the data
    component.write("other/{name}.fgb")

    # Assert the files
    assert Path(tmp_path, "other", "buildings.fgb").is_file()


def test_exposure_geom_component_write_warnings(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
):
    caplog.set_level(logging.DEBUG)
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="w"),
    )
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)

    # Write while not data present
    component.write()
    assert "No geoms data found, skip writing." in caplog.text

    # Add empty geometry to data
    component.set(gpd.GeoDataFrame(), name="empty_ds")

    # Write with no geometries in dataset
    component.write()
    assert "empty_ds is empty. Skipping..." in caplog.text


def test_exposure_geom_component_setup(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGeomsComponent(model=model_exposure_setup)

    # Assert that the data is empty
    assert len(component.data) == 0
    assert "exposure" not in component.model.config.data

    # Setup the data
    component.setup(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
    )

    assert len(component.data) == 1
    assert "buildings" in component.data
    assert len(component.data["buildings"]) != 0


def test_exposure_geom_component_setup_errors(
    model: FIATModel,
    build_region_small: Path,
):
    # Setup the component
    component = ExposureGeomsComponent(model=model)

    # Assert that no available region lead to an error
    with pytest.raises(
        MissingRegionError,
        match="Region is None -> use 'setup_region' before this method",
    ):
        component.setup(
            exposure_fname="bag",
            exposure_type_column="gebruiksdoel",
            exposure_link_fname="bag_link",
        )

    # Add region to skip that error
    component.model.setup_region(build_region_small)

    # Assert that no vulnerability data present results in an error
    with pytest.raises(
        RuntimeError,
        match="Use `setup_vulnerability` before this method",
    ):
        component.setup(
            exposure_fname="bag",
            exposure_type_column="gebruiksdoel",
            exposure_link_fname="bag_link",
        )


def test_exposure_geom_component_setup_max(
    model_exposure_setup: FIATModel,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
):
    # Setup the component
    component = ExposureGeomsComponent(model=model_exposure_setup)
    # Added the exposure to the data to expand upon
    component.set(exposure_vector_clipped_for_damamge, name="buildings")

    # Assert max damage column is not present
    assert "max_damage_structure" not in component.data["buildings"].columns

    # Call the setup method
    component.setup_max_damage(
        exposure_name="buildings",
        exposure_type="damage",
        exposure_cost_table_fname="damage_values",
        country="World",
    )

    # Assert that the data is there
    assert "max_damage_structure" in component.data["buildings"].columns


def test_exposure_geom_component_setup_max_errors(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGeomsComponent(model=model_exposure_setup)

    # Error as the dataset is not found
    with pytest.raises(
        RuntimeError,
        match="Run `setup_exposure_geoms` before this methods \
with 'bag' as input or chose from already present geometries: ",
    ):
        component.setup_max_damage(
            exposure_name="bag",
            exposure_type="damage",
            exposure_cost_table_fname="jrc_damage_values",
            country="World",
        )


def test_exposure_geom_component_update_cols(
    model_with_region: FIATModel,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
):
    # Setup the component
    component = ExposureGeomsComponent(model=model_with_region)
    # Added the exposure to the data to expand upon
    component.set(exposure_vector_clipped_for_damamge, name="bag")

    # Assert max damage column is not present
    assert "ground_flht" not in component.data["bag"].columns

    # Call the setup method
    component.update_column(
        exposure_name="bag",
        columns=["ground_flht"],
        values=0,
    )

    # Assert that the data is there
    assert "ground_flht" in component.data["bag"].columns

    # Assert that the data is NOT there
    assert "ground_elevtn" not in component.data["bag"].columns
    assert "extract_method" not in component.data["bag"].columns

    # Set multiple at once
    component.update_column(
        exposure_name="bag",
        columns=["ground_elevtn", "extract_method"],
        values=[0, "centroid"],
    )

    # Assert that the data is there
    assert "ground_elevtn" in component.data["bag"].columns
    assert "extract_method" in component.data["bag"].columns


def test_exposure_geom_component_update_cols_errors(
    model_with_region: FIATModel,
):
    # Setup the component
    component = ExposureGeomsComponent(model=model_with_region)

    # Error as the dataset is not found
    with pytest.raises(
        RuntimeError,
        match="Run `setup_exposure_geoms` before this methods \
with 'bag' as input or chose from already present geometries: ",
    ):
        component.update_column(
            exposure_name="bag",
            columns=["ground_flht"],
            values=0,
        )
