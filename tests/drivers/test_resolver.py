from hydromt_fiat.drivers.resolvers import OSMResolver


def test_osm_resolver():
    # Create the object
    obj = OSMResolver()

    # Return the correct uri
    res = obj.resolve("foo/bar/baz")

    # Assert the output
    assert isinstance(res, list)
    assert res[0] == "baz"
