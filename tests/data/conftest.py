import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from hydromt_fiat.data.get import LIB_DATA_DIR


# File fixtures
@pytest.fixture
def tmp_json(tmp_path: Path) -> Path:
    data = {"foo": "bar", "spooky": "ghost"}
    p = Path(tmp_path, "tmp.json")
    with open(p, "w") as writer:
        json.dump(data, writer)
    return p


@pytest.fixture
def tmp_txt(tmp_path: Path) -> Path:
    p = Path(tmp_path, "tmp.txt")
    with open(p, "w") as writer:
        writer.write("Spooky ghost!")
    return p


## Archive fixtures
@pytest.fixture
def tmp_tarfile(
    tmp_path: Path,
    tmp_json: Path,
    tmp_txt: Path,
) -> Path:
    p = Path(tmp_path, "tmp.tar.gz")
    with tarfile.open(
        p,
        "w:gz",
    ) as writer:
        writer.add(tmp_json, tmp_json.name)
        writer.add(tmp_txt, tmp_txt.name)
    return p


@pytest.fixture
def tmp_zipfile(
    tmp_path: Path,
    tmp_json: Path,
    tmp_txt: Path,
) -> Path:
    p = Path(tmp_path, "tmp.zip")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as writer:
        writer.write(tmp_json, tmp_json.name)
        writer.write(tmp_txt, tmp_txt.name)
    return p


# Data
@pytest.fixture(scope="session")
def registry() -> dict[str, dict[str, str]]:
    with open(Path(LIB_DATA_DIR, "registry.json"), "r") as reader:
        data = json.loads(reader.read())
    return data
