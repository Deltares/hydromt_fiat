from pyproj.crs import CRS, CompoundCRS

from hydromt_fiat.gis.utils import crs_representation


def test_crs_representation():
    # Call the function
    s = crs_representation(CRS.from_epsg(4326))

    # Assert the output
    assert s == "EPSG:4326"


def test_crs_representation_none():
    # Call the function
    s = crs_representation(None)

    # Assert the output
    assert s is None


def test_crs_representation_unknown():
    # Call the function
    s = crs_representation(
        CompoundCRS(
            name="foo",
            components=[CRS.from_epsg(4326), CRS.from_epsg(7837)],
        ),
    )

    # Assert the output
    assert s.startswith("COMPOUNDCRS")
