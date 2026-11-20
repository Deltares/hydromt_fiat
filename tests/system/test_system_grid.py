from pathlib import Path

import pytest

from hydromt_fiat import FIATModel
from hydromt_fiat.utils import FLOOD_DEPTH, GRID
from tests.system import SKIP_IF_FIAT_INCOMPATIBLE, GridModel, load_settings


@SKIP_IF_FIAT_INCOMPATIBLE
@pytest.mark.system
def test_system_grid_model(
    tmp_path: Path,
    build_data_catalog_path: Path,
    global_data_catalog_path: Path,
    build_region_small: Path,
):
    ## HydroMT-FIAT
    # Setup the model
    model = FIATModel(
        root=tmp_path,
        type=GRID,
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

    # Setup the exposure grid data
    model.exposure_grid.create(
        exposure_fname="commercial_structure",
        vulnerability_name="jrc_curves",
        exposure_link_fname="exposure_grid_link",
        name="commercial_structure",
    )
    model.exposure_grid.create(
        exposure_fname="commercial_content",
        vulnerability_name="jrc_curves",
        exposure_link_fname="exposure_grid_link",
        name="commercial_content",
    )

    # Write the model
    model.write()

    ## FIAT
    # Read the config file
    cfg = load_settings(Path(model.root.path, model.config._filename))

    # Read the data in the fiat model
    fmodel = GridModel(cfg)

    # Execute
    fmodel.run()
