from hydromt_fiat.settings import DEFAULT_SETTINGS, Exposure, Settings
from hydromt_fiat.utils import FLOOD_DEPTH, GEOM


def test_settings():
    # Just create an instance
    s = Settings()

    # Assert some default values
    assert s.model.type == GEOM
    assert s.model.method == FLOOD_DEPTH
    assert s.model.threads == 1
    assert s.model.risk == False

    # Assert the file
    assert s.exposure == Exposure()
    assert s.hazard is None
    assert s.vulnerability is None

    # Assert it's equal to the default
    assert s == DEFAULT_SETTINGS
