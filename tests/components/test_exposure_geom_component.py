from hydromt_fiat.components import ExposureGeomsComponent


def test_exposure_geom_component_empty(mock_model):
    # Setup the component
    component = ExposureGeomsComponent(model=mock_model)

    # Assert some basics
    assert component._filename == "exposure/{name}.fgb"
    assert len(component.data) == 0
    assert isinstance(component.data, dict)
