import logging
from pathlib import Path

import geopandas as gpd
import pytest
from hydromt import DataCatalog
from hydromt.data_catalog.sources import GeoDataFrameSource
from osmnx._errors import InsufficientResponseError

from hydromt_fiat.drivers import OSMDriver


@pytest.mark.parametrize("tag_name", ["building", "highway", "landuse", "amenity"])
def test_OMSDriver_get_osm_data(tag_name, build_region_gdf, caplog):
    geom_type = (
        ["LineString", "MultiLineString"]
        if tag_name == "highway"
        else ["MultiPolygon", "Polygon"]
    )
    tag = {tag_name: True}
    polygon = build_region_gdf.geometry[0]
    caplog.set_level(logging.INFO)

    osm_data = OSMDriver._get_osm_data(polygon=polygon, tag=tag, geom_type=geom_type)
    assert isinstance(osm_data, gpd.GeoDataFrame)
    assert f"Total number of {tag_name} found from OSM:" in caplog.text
    assert not osm_data.empty
    assert osm_data.columns.to_list() == ["geometry", tag_name]
    assert osm_data.intersects(polygon).all()


def test_OMSDriver_get_osm_data_errors(build_region_gdf, caplog):
    geom_type = ["MultiPolygon", "Polygon"]
    tag = {"building": True}
    with pytest.raises(
        TypeError, match="Given polygon is not of shapely.geometry.Polygon type"
    ):
        OSMDriver._get_osm_data(build_region_gdf, tag=tag, geom_type=geom_type)

    caplog.set_level(logging.ERROR)
    tag = {"buildin": True}
    with pytest.raises(
        InsufficientResponseError,
        match="No data elements in server response. Check log and query location/tags.",
    ):
        OSMDriver._get_osm_data(
            polygon=build_region_gdf.geometry[0], tag=tag, geom_type=geom_type
        )

    assert f"No OSM data retrieved with the following tags: {tag}" in caplog.text


def test_OSMDriver_get_osm_data_empty(mocker, build_region_gdf, caplog):
    geom_type = ["MultiPolygon", "Polygon"]
    tag = {"building": True}
    caplog.set_level(logging.WARNING)
    mocker.patch(
        "hydromt_fiat.drivers.osm_driver.ox.features.features_from_polygon",
        returns=gpd.GeoDataFrame(),
    )
    osm_data = OSMDriver._get_osm_data(
        build_region_gdf.geometry[0], tag=tag, geom_type=geom_type
    )
    assert not osm_data
    assert "No building features found for polygon" in caplog.text


def test_OSMDriver_read_raise_errors(build_region_gdf):
    osm_driver = OSMDriver()
    with pytest.raises(
        ValueError, match="Cannot use multiple uris for reading OSM data."
    ):
        osm_driver.read(uris=["uri1", "uri2"], mask=build_region_gdf)

    with pytest.raises(
        ValueError, match="Missing region argument for reading OSM geometries"
    ):
        osm_driver.read(uris=["uri"], mask=None)


def test_OSMDriver_read(build_region_gdf, mocker):
    osm_driver = OSMDriver()
    mock_method = mocker.patch.object(osm_driver, "_get_osm_data")
    osm_driver.read(uris=["building"], mask=build_region_gdf)
    mock_method.assert_called_with(
        polygon=build_region_gdf.geometry[0], tag={"building": True}, geom_type=None
    )


def test_OSMDriver_write(tmp_path, build_region_gdf, caplog):
    osm_driver = OSMDriver()
    # Test with supported extension
    fp = tmp_path / "test_data.fgb"
    osm_driver.write(path=fp, gdf=build_region_gdf)
    assert fp.exists
    gdf = gpd.read_file(fp)
    assert gdf.equals(build_region_gdf)

    # Test with unsupported extension
    fp = tmp_path / "test_data.csv"
    caplog.set_level(logging.WARNING)
    p = osm_driver.write(path=fp, gdf=build_region_gdf)
    assert "driver osm has no support for extension .csv"
    assert Path(p).suffix == ".fgb"
    assert Path(p).exists


def test_OSMDriver_datacatalog(tmp_path, build_region_gdf, build_data_catalog):
    dc = DataCatalog(build_data_catalog)
    # Create data catalog source for osm data and add to data catalog
    osm_source = GeoDataFrameSource(
        name="osm_buildings", uri="building", driver="osm", uri_resolver="osm_resolver"
    )
    dc.add_source(name="osm_buildings", source=osm_source)
    assert osm_source == dc.get_source("osm_buildings")

    # Read osm data from data catalog
    building_data = dc.get_geodataframe("osm_buildings", geom=build_region_gdf)
    assert isinstance(building_data, gpd.GeoDataFrame)

    # Write datacatalog source to file
    fp = tmp_path / "test_data.fgb"
    osm_building_source = dc.get_source("osm_buildings")
    osm_building_source.to_file(file_path=fp, mask=build_region_gdf)
    assert fp.exists
    gdf = gpd.read_file(fp)
    assert gdf.columns.to_list() == ["building", "geometry"]

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
    osm_roads_data = source.read_data(mask=build_region_gdf)
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
