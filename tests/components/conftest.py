import shutil
from pathlib import Path
from types import MethodType
from typing import Callable
from unittest.mock import MagicMock, PropertyMock

import pandas as pd
import pytest
from hydromt import DataCatalog
from hydromt.model import ModelRoot
from pyproj.crs import CRS
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ConfigComponent


## Models and Mocked objects
@pytest.fixture
def model_exposure_setup(
    model_with_region: FIATModel,
    vulnerability_curves: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
) -> Callable[[str], FIATModel]:
    def _factory(model_type: str) -> FIATModel:
        model = model_with_region
        model._type = model_type
        model.vulnerability.set(vulnerability_curves)
        model.vulnerability.set_id(vulnerability_identifiers)
        return model

    return _factory


@pytest.fixture
def mock_model_factory(
    mocker: MockerFixture, tmp_path: Path
) -> Callable[[Path, str], FIATModel]:
    def _factory(
        path: Path = tmp_path,
        mode: str = "w",
        model_type: str = "geom",
    ) -> MagicMock:
        model = mocker.create_autospec(FIATModel)
        model.root = ModelRoot(path, mode=mode)
        model.data_catalog = mocker.create_autospec(DataCatalog)
        model.crs = CRS.from_epsg(4326)
        model.type = model_type
        model._assert_model_type = MethodType(FIATModel._assert_model_type, model)
        return model

    return _factory


@pytest.fixture
def mock_model(mock_model_factory: Callable[[Path, str], FIATModel]) -> MagicMock:
    def _factory(model_type: str) -> MagicMock:
        model = mock_model_factory(model_type=model_type)
        return model

    return _factory


@pytest.fixture
def mock_model_config(
    mock_model_factory: Callable[[Path, str], FIATModel],
) -> Callable[[str], FIATModel]:
    def _factory(model_type: str) -> MagicMock:
        model = mock_model_factory(model_type=model_type)
        config = ConfigComponent(model)
        type(model).config = PropertyMock(side_effect=lambda: config)
        return model

    return _factory


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
def vulnerability_curves_only_path(
    tmp_path: Path,
    model_data_path: Path,
) -> Path:
    p = Path(tmp_path, "curves.nc")
    shutil.copy2(
        src=Path(model_data_path, "curves.nc"),
        dst=p,
    )
    assert p.is_file()
    return p
