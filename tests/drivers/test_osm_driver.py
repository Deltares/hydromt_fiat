import logging
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from hydromt import DataCatalog
from hydromt.data_catalog.sources import GeoDataFrameSource
from osmnx._errors import InsufficientResponseError
from pytest_mock import MockerFixture

from hydromt_fiat.drivers import OSMDriver


@pytest.mark.parametrize("tag_name", ["building", "highway", "landuse", "amenity"])
def test_osm_driver_get_osm_data(
    caplog: pytest.LogCaptureFixture,
    tag_name: str,
    build_region: gpd.geodataframe,
    osm_data_path: Path,
):
    geom_type = (
        ["LineString", "MultiLineString"]
        if tag_name == "highway"
        else ["MultiPolygon", "Polygon"]
    )
    tag = {tag_name: True}
    polygon = build_region.geometry[0]
    caplog.set_level(logging.INFO)

    osm_data = OSMDriver.get_osm_data(polygon=polygon, tag=tag, geom_type=geom_type)
    assert isinstance(osm_data, gpd.GeoDataFrame)
    assert f"Total number of {tag_name} found from OSM:" in caplog.text
    assert not osm_data.empty
    assert osm_data.columns.to_list() == ["geometry", tag_name]
    assert osm_data.intersects(polygon).all()


def test_osm_driver_get_osm_data_errors(
    caplog: pytest.LogCaptureFixture,
    build_region: gpd.GeoDataFrame,
    osm_data_path: Path,
):
    geom_type = ["MultiPolygon", "Polygon"]
    tag = {"building": True}
    with pytest.raises(
        TypeError,
        match=re.escape("Given geometry is not a (multi)polygon"),
    ):
        OSMDriver.get_osm_data(build_region, tag=tag, geom_type=geom_type)

    caplog.set_level(logging.ERROR)
    tag = {"buildin": True}
    with pytest.raises(
        InsufficientResponseError,
        match="No matching features. Check query location, tags, and log.",
    ):
        OSMDriver.get_osm_data(
            polygon=build_region.geometry[0], tag=tag, geom_type=geom_type
        )

    assert f"No OSM data retrieved with the following tags: {tag}" in caplog.text


def test_osm_driver_get_osm_data_empty(
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    build_region: gpd.GeoDataFrame,
    osm_data_path: Path,
):
    geom_type = ["MultiPolygon", "Polygon"]
    tag = {"building": True}
    caplog.set_level(logging.WARNING)
    mocker.patch(
        "hydromt_fiat.drivers.osm_driver.ox.features.features_from_polygon",
        returns=gpd.GeoDataFrame(),
    )
    osm_data = OSMDriver.get_osm_data(
        build_region.geometry[0], tag=tag, geom_type=geom_type
    )
    assert not osm_data
    assert "No building features found for polygon" in caplog.text


def test_osm_driver_read_raise_errors(
    build_region: gpd.GeoDataFrame,
    osm_data_path: Path,
):
    osm_driver = OSMDriver()
    with pytest.raises(
        ValueError, match="Cannot use multiple uris for reading OSM data."
    ):
        osm_driver.read(uris=["uri1", "uri2"], mask=build_region)

    with pytest.raises(ValueError, match="Mask is required to retrieve OSM data"):
        osm_driver.read(uris=["building"], mask=None)

    mask = [1, 2, 3, 4]
    err_msg = f"Wrong type: {type(mask)} -> should be GeoDataFrame or GeoSeries"
    with pytest.raises(TypeError, match=err_msg):
        osm_driver.read(uris=["uri"], mask=mask)


def test_osm_driver_read(
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    build_region: gpd.GeoDataFrame,
    osm_data_path: Path,
):
    osm_driver = OSMDriver()
    mock_method = mocker.patch.object(OSMDriver, "get_osm_data")
    osm_driver.read(uris=["building"], mask=build_region)
    mock_method.assert_called_with(
        polygon=build_region.geometry[0], tag={"building": True}, geom_type=None
    )
    # Test with a mask geodataframe containing two geometries
    mask = build_region.copy()
    mask = pd.concat([mask, build_region])
    caplog.set_level(logging.WARNING)
    osm_driver.read(uris=["building"], mask=mask)
    assert (
        "Received multiple geometries for mask, geometries will be dissolved into"
        " single geometry." in caplog.text
    )


def test_osm_driver_write(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    build_region: gpd.GeoDataFrame,
    osm_data_path: Path,
):
    osm_driver = OSMDriver()
    # Test with supported extension
    fp = tmp_path / "test_data.fgb"
    osm_driver.write(path=fp, gdf=build_region)
    assert fp.exists
    gdf = gpd.read_file(fp)
    assert gdf.equals(build_region)

    # Test with unsupported extension
    fp = tmp_path / "test_data.csv"
    caplog.set_level(logging.WARNING)
    p = osm_driver.write(path=fp, gdf=build_region)
    assert "driver osm has no support for extension .csv" in caplog.text
    assert Path(p).suffix == ".fgb"
    assert Path(p).exists


def test_osm_driver_datacatalog(
    tmp_path: Path,
    build_region: gpd.GeoDataFrame,
    build_data_catalog_path: Path,
    osm_data_path: Path,
):
    dc = DataCatalog(build_data_catalog_path)
    # Create data catalog source for osm data and add to data catalog
    osm_source = GeoDataFrameSource(
        name="osm_buildings", uri="building", driver="osm", uri_resolver="osm_resolver"
    )
    dc.add_source(name="osm_buildings", source=osm_source)
    assert osm_source == dc.get_source("osm_buildings")

    # Read osm data from data catalog
    building_data = dc.get_geodataframe("osm_buildings", geom=build_region)
    assert isinstance(building_data, gpd.GeoDataFrame)

    # Write datacatalog source to file
    fp = tmp_path / "test_data.fgb"
    osm_building_source = dc.get_source("osm_buildings")
    osm_building_source.to_file(file_path=fp, mask=build_region)
    assert fp.exists
    gdf = gpd.read_file(fp)
    assert gdf.columns.to_list() == ["building", "geometry"]


def test_osm_driver_datacatalog_yml_entry(
    build_region: gpd.GeoDataFrame,
    build_data_catalog_path: Path,
    osm_data_path: Path,
):
    dc = DataCatalog(build_data_catalog_path)
    # Add datacatalog source as dict
    data_source_dict = {
        "osm_roads": {
            "uri": "highway",
            "data_type": "GeoDataFrame",
            "uri_resolver": "osm_resolver",
            "driver": {
                "name": "osm",
                "options": {
                    "geom_type": ["LineString", "MultiLineString"],
                    "tags": ["motorway", "primary", "secondary", "tertiary"],
                },
            },
        },
    }
    dc = dc.from_dict(data_source_dict)
    source = dc.get_source("osm_roads")
    osm_roads_data = source.read_data(mask=build_region)
    assert not osm_roads_data.empty
    assert all(
        [
            road_type in ["motorway", "primary", "secondary", "tertiary"]
            for road_type in osm_roads_data["highway"].unique()
        ]
    )
    assert all(
        [
            geom_type in ["LineString", "MultiLineString"]
            for geom_type in osm_roads_data.geometry.type.unique()
        ]
    )
