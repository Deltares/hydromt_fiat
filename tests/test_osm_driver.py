import logging

import geopandas as gpd
import pytest

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


def test_OMSDriver_get_osm_data_errors(build_region_gdf):
    geom_type = ["MultiPolygon", "Polygon"]
    tag = {"building": True}
    with pytest.raises(
        ValueError, match="Given polygon is not of shapely.geometry.Polygon type"
    ):
        OSMDriver._get_osm_data(build_region_gdf, tag=tag, geom_type=geom_type)


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
        osm_driver.read(uris=["uri1", "uri2"], region=build_region_gdf)

    with pytest.raises(
        ValueError, match="Missing region argument for reading OSM geometries"
    ):
        osm_driver.read(uris=["uri"], region=None)


def test_OSMDriver_read(build_region_gdf, mocker):
    osm_driver = OSMDriver()
    mock_method = mocker.patch.object(osm_driver, "_get_osm_data")
    osm_driver.read(uris=["building"], region=build_region_gdf)
    mock_method.assert_called_with(
        polygon=build_region_gdf.geometry[0], tag={"building": True}, geom_type=None
    )
