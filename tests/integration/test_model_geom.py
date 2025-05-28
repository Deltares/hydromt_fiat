from pathlib import Path

import pytest
from fiat import Configurations, GeomModel

from hydromt_fiat import FIATModel


@pytest.mark.integration
def test_model_geom_integration(
    tmp_path: Path,
    build_data_catalog: Path,
    build_region_small: Path,
):
    ## HydroMT-FIAT
    # Setup the model
    model = FIATModel(
        root=tmp_path,
        mode="w+",
        data_libs=build_data_catalog,
    )

    # Add model type and region
    model.setup_config(**{"model.model_type": "geom"})
    model.setup_region(build_region_small)

    # Setup the vulnerability
    model.vulnerability_data.setup_vulnerability(
        "vulnerability_curves",
        "vulnerability_curves_linking",
        unit="m",
        continent="europe",
    )

    # Add an hazard layer
    model.hazard_grid.setup_hazard(
        "flood_event",
        elevation_reference="dem",
    )

    # Setup the exposure geometry data
    model.exposure_geoms.setup_exposure_geoms(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
    )
    model.exposure_geoms.setup_exposure_max_damage(
        exposure_name="buildings",
        exposure_type="damage",
        exposure_cost_table_fname="damage_values",
        country="Netherlands",  # Select the correct row from the data
    )
    # Needed for flood calculations
    model.exposure_geoms.update_exposure_column(
        exposure_name="buildings",
        columns=["ground_flht", "ground_elevtn", "extract_method"],
        values=[0, 0, "centroid"],
    )

    # Write the model
    model.write()

    ## FIAT
    # Read the config file
    cfg = Configurations.from_file(Path(model.root.path, model.config._filename))
    # Read the data in the fiat model
    fmodel = GeomModel(cfg)

    # Execute
    fmodel.run()
