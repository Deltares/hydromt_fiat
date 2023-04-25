from hydromt_fiat.fiat import FiatModel
from pathlib import Path
import pytest

EXAMPLEDIR = Path().absolute() / "examples"


@pytest.mark.skip(reason="Needs to be updated")
def test_write():
    root = EXAMPLEDIR.joinpath("fiat_flood")
    fm = FiatModel(root=root, mode="r+")
    fm.read()
    fm.write()
