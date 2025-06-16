import platform
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pandas as pd
import pytest
from hydromt import DataCatalog
from hydromt.model import ModelRoot
from pyproj.crs import CRS
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel


## OS related fixture
@pytest.fixture(scope="session")
def mount_string() -> str:
    if platform.system().lower() == "windows":
        return "d:/"
    return "/d/"  # Posix paths


## Models and Mocked objects
@pytest.fixture
def model_exposure_setup(
    model_with_region: FIATModel,
    vulnerability_curves: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
) -> FIATModel:
    model = model_with_region
    model.vulnerability_data.set(
        vulnerability_curves,
        name="vulnerability_curves",
    )
    model.vulnerability_data.set(
        vulnerability_identifiers,
        name="vulnerability_identifiers",
    )
    return model


@pytest.fixture
def mock_model(tmp_path: Path, mocker: MockerFixture) -> MagicMock:
    model = mocker.create_autospec(FIATModel)
    model.root = mocker.create_autospec(ModelRoot(tmp_path), instance=True)
    model.root.path.return_value = tmp_path
    model.data_catalog = mocker.create_autospec(DataCatalog)
    # Set attributes for practical use
    type(model).crs = PropertyMock(side_effect=lambda: CRS.from_epsg(4326))
    type(model).root = PropertyMock(side_effect=lambda: ModelRoot(tmp_path))
    return model


## Extra data structures
@pytest.fixture
def config_dummy(tmp_path: Path) -> dict:
    data = {
        "foo": "bar",
        "baz": {
            "file1": Path(tmp_path, "tmp.txt").as_posix(),
            "file2": "tmp/tmp.txt",
        },
        "spooky": {"ghost": [1, 2, 3]},
    }
    return data
