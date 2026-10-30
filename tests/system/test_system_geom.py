from pathlib import Path

import pytest
from packaging.version import Version

from hydromt_fiat import FIATModel
from hydromt_fiat.utils import FLOOD_LEVEL, GEOM

try:
    import fiat

    HAS_FIAT = True

except ImportError:
    HAS_FIAT = False

if HAS_FIAT:
    from fiat import GeomModel, __version__
    from fiat.settings import load_settings
else:
    __version__ = "NOT INSTALLED"

@pytest.mark.skipif(
    not HAS_FIAT or Version(__version__) < Version("1.0.0.dev0"),
    reason=f"At least Delft-FIAT version 1.0.0 is required (got {__version__}).",
)
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
    model.set_config(method=FLOOD_LEVEL)
    model.set_region(build_region_small)

    # Setup the vulnerability
    model.vulnerability.create(
        "jrc_curves",
        "jrc_curves_link",
        unit="m",
        continent="europe",
    )

    # Add an hazard layer
    model.hazard.create(
        "flood_event",
        hazard_type="water_level"
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
    )
    model.exposure_geoms.create_max_value(
        exposure_name="buildings",
        impact_type="damage",
        exposure_cost_table_fname="jrc_damage",
        country="Netherlands",  # Select the correct row from the data
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
