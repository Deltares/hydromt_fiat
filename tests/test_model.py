from pathlib import Path

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
    assert Path(tmp_path, "region/region.geojson").is_file()

    # Model in read mode
    model = FIATModel(tmp_path, mode="r")
    model.read()

    assert model.region is not None


def test_setup_vulnerability(tmp_path, build_data_catalog):
    # Setup the model
    model = FIATModel(tmp_path, mode="w+", data_libs=build_data_catalog)

    assert len(model.vulnerability_data.data) == 0

    # Setup the vulnerability
    model.setup_vulnerability(
        vuln_fname="jrc_vulnerability_curves",
        vuln_link_fname="jrc_vulnerability_curves_linking",
        continent="europe",
    )

    assert len(model.vulnerability_data.data) == 2
    assert "vulnerability_curves" in model.vulnerability_data.data
    assert "vulnerability_identifiers" in model.vulnerability_data.data
    assert (
        model.config.get_value("vulnerability.file")
        == "vulnerability/vulnerability_curves.csv"
    )
