from pathlib import Path

import pytest

from hydromt_fiat import FIATModel
from hydromt_fiat.utils import FLOOD_DEPTH, GEOM
from tests.system import SKIP_IF_FIAT_INCOMPATIBLE, GeomModel, load_settings


@SKIP_IF_FIAT_INCOMPATIBLE
@pytest.mark.system
def test_system_geom_model(
    tmp_path: Path,
    build_data_catalog_path: Path,
    global_data_catalog_path: Path,
    build_region_small: Path,
):
    ## HydroMT-FIAT
    # Setup the model
    model = FIATModel(
        root=tmp_path,
        type=GEOM,
        data_libs=[build_data_catalog_path, global_data_catalog_path],
        mode="w+",
    )

    # Add model type and region
    model.set_config(method=FLOOD_DEPTH)
    model.set_region(build_region_small)

    # Setup the vulnerability
    model.vulnerability.create(
        hazard_type="water_depth",
        vulnerability_fname="jrc_curves",
        vulnerability_link_fname="jrc_curves_link",
        unit="m",
        continent="europe",
        method=FLOOD_DEPTH,
    )

    # Add an hazard layer
    model.hazard.create(
        hazard_fname="flood_event",
        hazard_type="water_depth",
        unit="m",
    )

    # Setup the exposure geometry data
    model.exposure_geoms.create(
        exposure_fname="buildings",
        exposure_object_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
    )
    model.exposure_geoms.create_link(
        exposure_name="buildings",
        impact_type="damage",
        vulnerability_name="jrc_curves",
    )
    model.exposure_geoms.create_max_value(
        exposure_name="buildings",
        impact_type="damage",
        exposure_cost_table_fname="jrc_damage",
        country="Netherlands",  # Select the correct row from the data
        vulnerability_name="jrc_curves",
    )
    # Needed for flood calculations
    model.exposure_geoms.update_column(
        exposure_name="buildings",
        columns=["reference", "elevation", "method"],
        values=[0, 0, "centroid"],
    )

    # Write the model
    model.write()

    ## FIAT
    # Read the config file
    cfg = load_settings(Path(model.root.path, model.config._filename))

    # Read the data in the fiat model
    fmodel = GeomModel(cfg)

    # Execute
    fmodel.run()
