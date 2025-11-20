from pathlib import Path

import pytest

from hydromt_fiat import FIATModel


@pytest.mark.integration
def test_build_model_geom(
    tmp_path: Path,
    build_data_catalog_path: Path,
    global_data_catalog_path: Path,
    build_region_small: Path,
):
    ## HydroMT-FIAT
    # Setup the model
    model = FIATModel(
        root=tmp_path,
        mode="w+",
        data_libs=[build_data_catalog_path, global_data_catalog_path],
    )

    # Add model type and region
    model.setup_config(**{"model.model_type": "geom"})
    model.setup_region(build_region_small)

    # Setup the vulnerability
    model.vulnerability.setup(
        "jrc_curves",
        "jrc_curves_link",
        unit="m",
        continent="europe",
    )

    # Add an hazard layer
    model.hazard.setup(
        "flood_event",
        elevation_reference="dem",
    )

    # Setup the exposure geometry data
    model.exposure_geoms.setup(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
        exposure_type_fill="unknown",
    )
    model.exposure_geoms.setup_max_damage(
        exposure_name="buildings",
        exposure_type="damage",
        exposure_cost_table_fname="jrc_damage",
        country="Netherlands",  # Select the correct row from the data
    )
    # Needed for flood calculations
    model.exposure_geoms.update_column(
        exposure_name="buildings",
        columns=["ground_flht", "ground_elevtn", "extract_method"],
        values=[0, 0, "centroid"],
    )

    # Assert the state
    assert model.region is not None  # Can't build otherwise but still
    assert model.config.get("model.type") == "geom"
    assert len(model.vulnerability.data.curves) == 1001
    assert "rs1" in model.vulnerability.data.curves.columns
    assert "flood_event" in model.hazard.data.data_vars
    assert model.hazard.data["flood_event"].shape == (5, 4)
    assert "buildings" in model.exposure_geoms.data  # Kind of obvious
    assert len(model.exposure_geoms.data["buildings"]) == 12
    assert "max_damage_structure" in model.exposure_geoms.data["buildings"].columns

    # Write the model
    model.write()

    # Assert the written output (paths)
    assert Path(tmp_path, "region.geojson").is_file()
    assert Path(tmp_path, "settings.toml").is_file()
    assert Path(tmp_path, "vulnerability", "curves.csv").is_file()
    assert Path(tmp_path, "hazard.nc").is_file()
    assert Path(tmp_path, "exposure", "buildings.fgb").is_file()


@pytest.mark.integration
def test_build_model_grid(
    tmp_path: Path,
    build_data_catalog_path: Path,
    global_data_catalog_path: Path,
    build_region_small: Path,
):
    ## HydroMT-FIAT
    # Setup the model
    model = FIATModel(
        root=tmp_path,
        mode="w+",
        data_libs=[build_data_catalog_path, global_data_catalog_path],
    )

    # Add model type and region
    model.setup_config(**{"model.model_type": "grid"})
    model.setup_region(build_region_small)

    # Setup the vulnerability
    model.vulnerability.setup(
        "jrc_curves",
        "jrc_curves_link",
        unit="m",
        continent="europe",
    )

    # Add an hazard layer
    model.hazard.setup(
        "flood_event",
        elevation_reference="dem",
    )

    # Setup the exposure grid data
    model.exposure_grid.setup(
        exposure_fnames=["commercial_structure", "commercial_content"],
        exposure_link_fname="exposure_grid_link",
    )

    # Assert the state
    assert model.region is not None  # Can't build otherwise but still
    assert model.config.get("model.type") == "grid"
    assert len(model.vulnerability.data.curves) == 1001
    assert "rs1" in model.vulnerability.data.curves.columns
    assert "flood_event" in model.hazard.data.data_vars
    assert model.hazard.data["flood_event"].shape == (5, 4)
    assert len(model.exposure_grid.data.data_vars) == 2
    assert "commercial_content" in model.exposure_grid.data.data_vars
    assert model.exposure_grid.data["commercial_content"].attrs["fn_damage"] == "cm1"

    # Write the model
    model.write()

    # Assert the written output (paths)
    assert Path(tmp_path, "region.geojson").is_file()
    assert Path(tmp_path, "settings.toml").is_file()
    assert Path(tmp_path, "vulnerability", "curves.csv").is_file()
    assert Path(tmp_path, "hazard.nc").is_file()
    assert Path(tmp_path, "exposure", "spatial.nc").is_file()
