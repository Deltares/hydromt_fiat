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


def test_exposure_geom_component_set(
    caplog: pytest.LogCaptureFixture,
    build_region_gdf: gpd.GeoDataFrame,
    mock_model: MagicMock,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)
    assert len(component.data) == 0  # No data yet

    # Add a geometry dataset
    component.set(geom=build_region_gdf, name="ds1")

    # Assert that it's there
    assert len(component.data) == 1
    assert "ds1" in component.data

    # Overwrite with the same dataset, should produce no warning
    component.set(geom=build_region_gdf, name="ds1")
    assert "Replacing geom: ds1" not in caplog.text

    # Overwrite, but with a copy, should produce a warning
    component.set(geom=build_region_gdf.copy(), name="ds1")
    assert "Replacing geom: ds1" in caplog.text


def test_exposure_geom_component_region(
    build_region_gdf: gpd.GeoDataFrame,
    box_geometry: gpd.GeoDataFrame,
    mock_model: MagicMock,
):
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)
    assert component.region is None

    # Set a second dataset
    component.set(geom=build_region_gdf, name="ds1")

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
    model_cached: Path,
    mock_model: MagicMock,
):
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)

    # Assert it's empty
    assert component._data is None

    # Calling read to read in the data
    component.read()

    # Assert that the data is a dictionary with two elements
    assert isinstance(component._data, dict)
    assert len(component._data) == 3
    assert "buildings" in component.data
    # Merging of csv and geoms went well
    assert "extract_method" in component.data["buildings_split"].columns


def test_exposure_geom_component_write(
    tmp_path: Path,
    model_cached: Path,
    mock_model: MagicMock,
):
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)
    # Read the data
    component.read()

    # Set the model root to the tmp directory
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="w"),
    )
    # Write the data
    component.write()

    # Assert the files
    assert Path(tmp_path, component._filename.format(name="buildings")).is_file()
    assert Path(tmp_path, component._filename.format(name="buildings_split")).is_file()


def test_exposure_geom_component_write_split(
    tmp_path: Path,
    model_cached: Path,
    mock_model: MagicMock,
):
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_cached, mode="r"),
    )
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)
    # Read the data
    component.read()

    # Set the model root to the tmp directory
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="w"),
    )
    # Write the data
    component.write(split=True)

    # Assert the files
    assert Path(tmp_path, component._filename.format(name="buildings")).is_file()
    assert (
        Path(tmp_path, component._filename.format(name="buildings"))
        .with_suffix(".csv")
        .is_file()
    )


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
    component.setup_exposure_geoms(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
    )

    assert len(component.data) == 1
    assert "buildings" in component.data
    assert len(component.data["buildings"]) != 0
    assert "exposure" in component.model.config.data


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
        component.setup_exposure_geoms(
            exposure_fname="bag",
            exposure_type_column="gebruiksdoel",
            exposure_link_fname="bag_link",
        )

    # Add region to skip that error
    component.model.setup_region(build_region_small)

    # Assert that no vulnerability data present results in an error
    with pytest.raises(
        RuntimeError,
        match="Use setup_vulnerability before this method",
    ):
        component.setup_exposure_geoms(
            exposure_fname="bag",
            exposure_type_column="gebruiksdoel",
            exposure_link_fname="bag_link",
        )


def test_exposure_geom_component_setup_max(
    model_exposure_setup: FIATModel,
    exposure_geom_data_reduced: gpd.GeoDataFrame,
):
    # Setup the component
    component = ExposureGeomsComponent(model=model_exposure_setup)
    # Added the exposure to the data to expand upon
    component.set(exposure_geom_data_reduced, name="buildings")

    # Assert max damage column is not present
    assert "max_damage_structure" not in component.data["buildings"].columns

    # Call the setup method
    component.setup_exposure_max_damage(
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
        component.setup_exposure_max_damage(
            exposure_name="bag",
            exposure_type="damage",
            exposure_cost_table_fname="jrc_damage_values",
            country="World",
        )


def test_exposure_geom_component_update_cols(
    model_with_region: FIATModel,
    exposure_geom_data_reduced: gpd.GeoDataFrame,
):
    # Setup the component
    component = ExposureGeomsComponent(model=model_with_region)
    # Added the exposure to the data to expand upon
    component.set(exposure_geom_data_reduced, name="bag")

    # Assert max damage column is not present
    assert "ground_flht" not in component.data["bag"].columns

    # Call the setup method
    component.update_exposure_column(
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
    component.update_exposure_column(
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
        component.update_exposure_column(
            exposure_name="bag",
            columns=["ground_flht"],
            values=0,
        )
