from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import pytest
import shutil


EXAMPLEDIR = Path(
    "P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database"
)

_cases = {
    "read_read_write_single_file": {
        "dir": "test_read",
        "new_root": EXAMPLEDIR / "test_read_write_single",
    },
    "read_read_write_multiple_files": {
        "dir": "test_read_multiple",
        "new_root": EXAMPLEDIR / "test_read_write_multiple",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_read_write(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["dir"])
    logger = setuplog("hydromt_fiat", log_level=10)

    fm = FiatModel(root=root, mode="r", logger=logger)
    fm.read()

    # Get the name of the spatial exposure data in the model that is read
    exposure_files = [k for k in fm.config["exposure"]["geom"].keys() if "file" in k]
    original_exposure_names = set(
        [
            fm.config["exposure"]["geom"][f].split("/")[-1].split(".")[0]
            for f in exposure_files
        ]
    )

    # Remove the new root folder if it already exists
    if _cases[case]["new_root"].exists():
        shutil.rmtree(_cases[case]["new_root"])

    # Set the new root and write the model
    fm.set_root(_cases[case]["new_root"])
    fm.write()

    # Check if the name of the spatial exposure data in the new_root is correct
    new_exposure_names = set(
        [f.stem for f in _cases[case]["new_root"].joinpath("exposure").glob("*.gpkg")]
    )

    assert original_exposure_names.issubset(new_exposure_names)
