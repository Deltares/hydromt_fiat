from hydromt_fiat.fiat import FiatModel
from pathlib import Path

EXAMPLEDIR = Path().absolute() / "examples"


def test_write():
    root = EXAMPLEDIR.joinpath("fiat_flood")
    fm = FiatModel(root=root, mode="r+")
    fm.read()
    fm.write()
    # TO ASK: how does the reading and writing happen at the same time??
