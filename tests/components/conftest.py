import platform
import shutil
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import pandas as pd
import pytest
from hydromt import DataCatalog
from hydromt.model import ModelRoot
from pyproj.crs import CRS
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ConfigComponent


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
    model.vulnerability.set(
        vulnerability_curves,
        name="curves",
    )
    model.vulnerability.set(
        vulnerability_identifiers,
        name="identifiers",
    )
    return model


@pytest.fixture
def mock_model_factory(
    mocker: MockerFixture, tmp_path: Path
) -> Callable[[Path, str], FIATModel]:
    def _factory(path: Path = tmp_path, mode: str = "w") -> MagicMock:
        model = mocker.create_autospec(FIATModel)
        model.root = ModelRoot(path, mode=mode)
        model.data_catalog = mocker.create_autospec(DataCatalog)
        model.crs = CRS.from_epsg(4326)
        return model

    return _factory


@pytest.fixture
def mock_model(mock_model_factory: Callable[[Path, str], FIATModel]) -> MagicMock:
    model = mock_model_factory()
    return model


@pytest.fixture
def mock_model_config(
    mock_model_factory: Callable[[Path, str], FIATModel],
) -> MagicMock:
    model = mock_model_factory()
    config = ConfigComponent(model)
    type(model).config = PropertyMock(side_effect=lambda: config)
    return model


## Extra data structures
@pytest.fixture
def config_dummy(tmp_path: Path) -> dict:
    data = {
        "foo": "bar",
        "baz": {
            "file1": Path(tmp_path, "tmp.txt"),
            "file2": "tmp/tmp.txt",
        },
        "spooky": {"ghost": [1, 2, 3]},
        "multi": [{"file": "tmp/tmp.txt"}, {"file": "boo.txt"}],
    }
    return data


## Extra data paths
@pytest.fixture
def exposure_cost_link_path(
    tmp_path: Path,
    exposure_cost_link: pd.DataFrame,
) -> Path:
    p = Path(tmp_path, "cost_link.csv")
    exposure_cost_link.to_csv(p, index=False)
    assert p.is_file()
    return p


@pytest.fixture
def exposure_vector_clipped_csv_path(
    tmp_path: Path,
    exposure_vector_clipped: gpd.GeoDataFrame,
) -> Path:
    p = Path(tmp_path, "foo.fgb")
    # Seperate the geometry data
    geom = exposure_vector_clipped.loc[:, ["object_id", "geometry"]]
    geom.to_file(p)
    assert p.is_file()
    # Separate the tabular data
    cols = exposure_vector_clipped.columns.values.tolist()
    cols.remove("geometry")
    data = exposure_vector_clipped.loc[:, cols]
    data.to_csv(p.with_suffix(".csv"), index=False)
    assert p.with_suffix(".csv").is_file()
    return p


@pytest.fixture
def vulnerability_curves_only_path(
    tmp_path: Path,
    model_data_path: Path,
) -> Path:
    p = Path(tmp_path, "curves.csv")
    shutil.copy2(
        src=Path(model_data_path, "vulnerability", "curves.csv"),
        dst=p,
    )
    assert p.is_file()
    return p
