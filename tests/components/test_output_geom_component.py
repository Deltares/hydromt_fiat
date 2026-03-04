from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import pytest
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import OutputGeomsComponent


def test_output_geoms_component_empty(mock_model: MagicMock):
    # Set up the component
    component = OutputGeomsComponent(model=mock_model)

    # Assert the state
    assert component._data is None
    assert isinstance(component.data, dict)  # Initialized


def test_output_geoms_component_read_none(
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


def test_output_geoms_component_read_not_found(
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


def test_output_geoms_component_read_sig(
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


def test_output_geoms_component_aggregate_square(
    tmp_path: Path,
    model_with_region: FIATModel,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    # Set up the component
    component = OutputGeomsComponent(model=model_with_region)

    # Set data like a dummy
    component._data = {"foo": exposure_vector_clipped}

    # Call the method
    component.aggregate_square(
        output_name="foo",
        res=0.1,
        output_dir=tmp_path,
    )

    # Assert the output
    p = Path(tmp_path, "foo_sq_aggr.fgb")
    assert p.is_file()
    data = gpd.read_file(p)
    assert len(data) == 18


def test_output_geoms_component_aggregate_square_errors(mock_model: MagicMock):
    # Set up the component
    component = OutputGeomsComponent(model=mock_model)

    # No data, so trying to do something for the dataset foo results in an error
    with pytest.raises(
        ValueError,
        match="'foo' not in the output component's data",
    ):
        component.aggregate_square(
            output_name="foo",
            res=0.1,
        )
