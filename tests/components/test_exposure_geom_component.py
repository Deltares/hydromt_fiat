import logging
from unittest.mock import MagicMock

import geopandas as gpd
import pytest

from hydromt_fiat.components import ExposureGeomsComponent


def test_exposure_geom_component_empty(mock_model):
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)

    # Assert some basics
    assert component._filename == "exposure/{name}.fgb"
    assert len(component.data) == 0
    assert isinstance(component.data, dict)


def test_exposure_geom_component_set(
    caplog: pytest.LogCaptureFixture,
    build_region_gdf: gpd.GeoDataFrame,
    build_region_small_gdf: gpd.GeoDataFrame,
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

    # Set a second dataset
    component.set(geom=build_region_small_gdf, name="ds2")

    # Assert the content
    assert len(component.data) == 2
    assert "ds2" in component.data
