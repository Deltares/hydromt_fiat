from hydromt_fiat.fiat import FiatModel
from pathlib import Path

EXAMPLEDIR = Path().absolute() / "examples"


def test_write():
    root = EXAMPLEDIR.joinpath("fiat_flood")
    FiatModel(root=root, mode="w+")
    # fm.write()
    # TO ASK: how does the reading and writing happen at the same time??
