from unittest.mock import MagicMock

from hydromt_fiat.components import OutputGeomsComponent


def test_output_geoms_component_empty(mock_model: MagicMock):
    # Set up the component
    component = OutputGeomsComponent(model=mock_model)

    # Assert the state
    assert component._data is None
    assert isinstance(component.data, dict)  # Initialized


def test_output_geoms_component_read(mock_model_config: MagicMock):
    # Set up the component
    component = OutputGeomsComponent(model=mock_model_config)

    # Assert the state
    assert component
