from hydromt_fiat.settings import DEFAULT_GEOM_SETTINGS, GeomSettings
from hydromt_fiat.utils import FLOOD_DEPTH, GEOM


def test_settings():
    # Just create an instance
    s = GeomSettings()

    # Assert some default values
    assert s.type == GEOM
    assert s.method == FLOOD_DEPTH
    assert s.threads == 1
    assert s.risk == False

    # Assert the file
    assert s.exposure is None
    assert s.hazard is None
    assert s.vulnerability is None

    # Assert it's equal to the default
    assert s == DEFAULT_GEOM_SETTINGS
