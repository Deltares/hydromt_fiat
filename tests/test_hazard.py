from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest

EXAMPLEDIR = Path().absolute() / "examples"

_cases = {
    "fiat_flood": {
        "region_grid": Path("data").joinpath("flood_hand", "hand_050cm_rp02.tif"),
        "example": "fiat_flood",
        "ini": "fiat_flood.ini",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_Hazard(case):
    # Read model in examples folder.
    root = EXAMPLEDIR.joinpath(_cases[case]["example"])
    fm = FiatModel(root=root, mode="r")
    fm.setup_hazard()

    assert fm.da



