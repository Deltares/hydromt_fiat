import logging
import re
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import numpy as np
import pytest
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import OutputGeomsComponent


def test_output_geom_component_empty(mock_model: MagicMock):
    # Set up the component
    component = OutputGeomsComponent(model=mock_model)

    # Assert the state
    assert component._data is None
    assert component._processed_data is None
    assert isinstance(component.data, dict)  # Initialized
    assert isinstance(component.processed_data, dict)  # Initialized
    assert isinstance(component.combined_data, dict)


def test_output_geom_component__assert_output_entry(
    mock_model: MagicMock,
):
    # Set up the component
    component = OutputGeomsComponent(model=mock_model)

    # Set data like a dummy
    component._data = {"foo": gpd.GeoDataFrame()}
    component._processed_data = {"bar": gpd.GeoDataFrame()}

    # Assert it's fine to call foo
    component._assert_output_entry(name="foo")
    component._assert_output_entry(name="bar")


def test_output_geom_component__assert_output_entry_errors(
    mock_model: MagicMock,
):
    # Set up the component
    component = OutputGeomsComponent(model=mock_model)
    # Set data like a dummy
    component._data = {"foo": gpd.GeoDataFrame()}
    component._processed_data = {"bar": 2}

    # Data name not present
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Chose from already present geometries: ['foo', 'bar'] \
i.e. a GeoDataFrame or run the appropriate `setup` method with 'baz' as input"
        ),
    ):
        component._assert_output_entry(name="baz")

    # Wrong type
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Chose from already present geometries: ['foo', 'bar'] \
i.e. a GeoDataFrame or run the appropriate `setup` method with 'bar' as input"
        ),
    ):
        component._assert_output_entry(name="bar")


def test_output_geom_component__set(
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = OutputGeomsComponent(model=mock_model)
    assert len(component.processed_data) == 0  # No data yet

    # Add a geometry dataset
    component._set(data=build_region, name="ds1")

    # Assert that it's there
    assert len(component.processed_data) == 1
    assert "ds1" in component.processed_data

    # Overwrite with the same dataset, should produce no warning
    component._set(data=build_region, name="ds1")
    assert "Replacing post processed geometry data: ds1" not in caplog.text

    # Overwrite, but with a copy, should produce a warning
    component._set(data=build_region.copy(), name="ds1")
    assert "Replacing post processed geometry data: ds1" in caplog.text


def test_output_geom_component__set_fid(
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
    build_region: gpd.GeoDataFrame,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = OutputGeomsComponent(model=mock_model)
    assert len(component.processed_data) == 0  # No data yet
    # Add fid column
    build_region["fid"] = [1]
    assert "fid" in build_region.columns

    # Add a geometry dataset
    component._set(data=build_region, name="ds1")

    # Assert logging statement
    assert "fid' column encountered in ds1" in caplog.text
    # Assert no fid column
    assert "fid" not in component.processed_data["ds1"].columns


def test_output_geom_component_read_none(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Set up the component
    component = OutputGeomsComponent(model=mock_model_config)

    # Assert the state
    assert len(component.data) == 0

    # Read (nothing)
    component.read()

    # Assert the state after
    assert len(component.data) == 0


def test_output_geom_component_read_not_found(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Set up the component
    component = OutputGeomsComponent(model=mock_model_config)

    # Assert the state
    assert len(component.data) == 0

    # Read (nothing) as the signature points to nothing
    component.read(filename="output/foo.gpkg")

    # Assert the state after
    assert len(component.data) == 0


def test_output_geom_component_read_sig(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Set up the component
    component = OutputGeomsComponent(model=mock_model_config)

    # Assert the state
    assert len(component.data) == 0

    # Read (nothing) as the signature points to nothing
    component.read(filename="exposure/buildings.fgb")

    # Assert the state after
    assert len(component.data) == 1
    assert "buildings" in component.data
    assert len(component.data["buildings"]) == 12


def test_output_geom_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Setup the component
    component = OutputGeomsComponent(model=mock_model_config)
    # Set data like a dummy
    component._processed_data = {
        "aggr1": exposure_vector_clipped,
        "aggr2": exposure_vector_clipped,
    }

    # Write the data
    component.write()

    # Assert the files
    assert Path(tmp_path, "post").is_dir()
    assert Path(tmp_path, component._filename.format(name="aggr1")).is_file()
    assert Path(tmp_path, component._filename.format(name="aggr2")).is_file()


def test_output_geom_component_write_df(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Setup the component
    component = OutputGeomsComponent(model=mock_model_config)
    # Drop the geometry column
    exposure_vector_clipped.drop(["geometry"], axis=1, inplace=True)
    # Set data like a dummy
    component._processed_data = {
        "aggr1": exposure_vector_clipped,
    }

    # Write the data
    component.write()

    # Assert the files
    assert (
        Path(
            tmp_path,
            component._filename.format(name="aggr1"),
        )
        .with_suffix(".csv")
        .is_file()
    )


def test_output_geom_component_write_warnings(
    caplog: pytest.LogCaptureFixture,
    mock_model_config: MagicMock,
):
    caplog.set_level(logging.INFO)

    # Setup the component
    component = OutputGeomsComponent(model=mock_model_config)

    # Call write with no post processed data
    component.write()

    # Assert the logging message
    assert "No post processed data found, skip writing." in caplog.text


def test_output_geom_component_spatial_aggregate(
    model_with_region: FIATModel,
    exposure_vector_clipped: gpd.GeoDataFrame,
    vector_grid: gpd.GeoDataFrame,
):
    # Set up the component
    component = OutputGeomsComponent(model=model_with_region)

    # Set data like a dummy
    component._data = {"foo": exposure_vector_clipped}

    # Call the method
    component.spatial_aggregate(
        output_name="foo",
        aggregation_areas_fname=vector_grid,
    )

    # Assert the output
    assert "foo_sp_aggr" in component.processed_data
    data = component.processed_data["foo_sp_aggr"]
    assert len(data) == 20
    np.testing.assert_almost_equal(
        data["max_damage_content"].iloc[0],
        desired=155730,
        decimal=0,
    )
    np.testing.assert_almost_equal(
        np.nanmean(data["max_damage_content"]),
        desired=796843,
        decimal=0,
    )


def test_output_geom_component_spatial_square_aggregate(
    model_with_region: FIATModel,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Set up the component
    component = OutputGeomsComponent(model=model_with_region)

    # Set data like a dummy
    component._data = {"foo": exposure_vector_clipped}

    # Call the method
    component.spatial_square_aggregate(
        output_name="foo",
        res=0.1,
        unit="km",
    )

    # Assert the output
    assert "foo_sq_aggr" in component.processed_data
    data = component.processed_data["foo_sq_aggr"]
    assert len(data) == 18
    np.testing.assert_almost_equal(
        data["max_damage_content"].iloc[0],
        desired=155730,
        decimal=0,
    )
    np.testing.assert_almost_equal(
        np.nanmean(data["max_damage_content"]),
        desired=796843,
        decimal=0,
    )


def test_output_geom_component_spatial_square_aggregate_no_clip(
    model: FIATModel,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Set up the component
    component = OutputGeomsComponent(model=model)

    # Set data like a dummy
    component._data = {"foo": exposure_vector_clipped}

    # Call the method
    component.spatial_square_aggregate(
        output_name="foo",
        res=0.1,
        unit="km",
    )

    # Assert the output
    assert "foo_sq_aggr" in component.processed_data
    data = component.processed_data["foo_sq_aggr"]
    assert len(data) == 20  # Is different from above as there is not region
    np.testing.assert_almost_equal(
        data["max_damage_content"].iloc[0],
        desired=155730,
        decimal=0,
    )
    np.testing.assert_almost_equal(
        np.nanmean(data["max_damage_content"]),
        desired=796843,
        decimal=0,
    )
