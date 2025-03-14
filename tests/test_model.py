from hydromt_fiat import FIATModel


def test_empty_model(tmp_path):
    # Setup an empty fiat model
    model = FIATModel(tmp_path)

    # Assert some basic statements
    assert "config" in model.components
    assert "region" in model.components
    assert model.region is None
    assert len(model.components) == 7


def test_basic_read_write(tmp_path, build_region):
    # Setup the model
    model = FIATModel(tmp_path, mode="w")

    # Call the necessary setup methods
    model.setup_config(model="geom")
    model.setup_region(region=build_region)
    # Write the model
    model.write()
    model = None

    # Model in read mode
    model = FIATModel(tmp_path, mode="r")
    model.read()

    assert model.region is not None
