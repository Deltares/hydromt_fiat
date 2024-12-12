from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import numpy as np
import pytest
import shutil
import copy
import rasterio


EXAMPLEDIR = Path().absolute() / "examples" / "data" / "update_ground_elevation"
DATADIR = Path().absolute() / "hydromt_fiat" / "data"
DATADIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/Database_env_fix/static/dem"
)

_cases = {
    "update_ground_elevation_with_dem": {
        "dir": "fiat_model",
        "new_root": EXAMPLEDIR / "test_update_ground_elevation",
        "ground_elevation": DATADIR / "charleston_14m.tif",
        "grnd_elev_unit": "meters",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_ground_elevation(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)

    fm.read()

    original_exposure = copy.deepcopy(fm.exposure.exposure_db)
    unique_ge_original = original_exposure["ground_elevtn"].unique()

    fm.exposure.setup_ground_elevation(
        _cases[case]["ground_elevation"],
        _cases[case]["grnd_elev_unit"],
    )

    # Remove the new root folder if it already exists
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    # Set the new root and write the model
    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # Check the values are updated. This will only work if the original data has "ground_elevtn" column
    unique_ge_new = fm.exposure.exposure_db["ground_elevtn"].unique()
    assert not np.array_equal(
        unique_ge_original, unique_ge_new
    ), "The ground_elevtn is the same"

    # Check if the updated values are not null
    not_null_values = fm.exposure.exposure_db["ground_elevtn"].notnull()
    assert (
        not_null_values.all()
    ), "Warning: There are null values in 'ground_elevtn' column."

    # Check if the calculated values are within the maximun and minimun value of the original daster file. This function could be used to calculate
    # Ground Elevation itself in case the ground_elevation_from_dem() function in gis.py is not accurate enough
    raster_file_path = _cases[case]["ground_elevation"]
    with rasterio.open(raster_file_path) as src:
        nodata_value = src.nodatavals[0]
        raster_data = src.read(1)
        valid_values = raster_data[raster_data != nodata_value]
        # mean_value_excluding_nodata = np.nanmean(valid_values)
        max_value_excluding_nodata = np.nanmax(valid_values)
        min_value_excluding_nodata = np.nanmin(valid_values)
        valid_values = (
            fm.exposure.exposure_db["ground_elevtn"] >= min_value_excluding_nodata
        ) & (fm.exposure.exposure_db["ground_elevtn"] <= max_value_excluding_nodata)
    assert valid_values.all(), "The ground_elevtn is beyond the maximun and minimun values of the provided DEM"
