import shutil
from pathlib import Path
from types import MethodType
from typing import Callable
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import pandas as pd
import pytest
import xarray as xr
from hydromt import DataCatalog
from hydromt.model import ModelRoot
from pyproj.crs import CRS
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ConfigComponent
from hydromt_fiat.components.config import SETTINGS_DICT
from hydromt_fiat.utils import DEFAULT


## Models and Mocked objects
@pytest.fixture
def model_exposure_setup(
    model_with_region: FIATModel,
    rename_vulnerability: Callable[[xr.Dataset, str], xr.Dataset],
    vulnerability_curves: xr.Dataset,
    vulnerability_identifiers: xr.Dataset,
) -> Callable[[str, str], FIATModel]:
    def _factory(model_type: str, name: str = DEFAULT) -> FIATModel:
        model = model_with_region
        model.set_type(model_type)
        model.vulnerability.set(rename_vulnerability(vulnerability_curves, name))
        ids = rename_vulnerability(vulnerability_identifiers, name)
        model.vulnerability.set_id(ids)
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
def mock_model_geom(mock_model: Callable[[str], FIATModel]) -> MagicMock:
    return mock_model("geom")


@pytest.fixture
def mock_model_config(
    mock_model_factory: Callable[[Path, str], FIATModel],
) -> Callable[[str], FIATModel]:
    def _factory(model_type: str) -> MagicMock:
        model = mock_model_factory(model_type=model_type)
        config = ConfigComponent(model)
        config._data = SETTINGS_DICT[model_type]()
        type(model).config = PropertyMock(side_effect=lambda: config)
        return model

    return _factory


@pytest.fixture
def mock_model_read(
    mock_model_config: Callable[[str], MagicMock],
    model_data_clipped_path: Path,
) -> Callable[[str, str | None, Path | None], MagicMock]:
    def _factory(
        model_type: str,
        settings: str | None = None,
        root: Path | None = None,
    ) -> MagicMock:
        model = mock_model_config(model_type)
        type(model).root = PropertyMock(
            side_effect=lambda: ModelRoot(root or model_data_clipped_path, mode="r"),
        )
        if settings is not None:
            model.config.read(settings)
        return model

    return _factory


## Extra data paths
@pytest.fixture
def output_geom_path(
    tmp_path: Path,
    model_data_clipped_path: Path,
    exposure_vector_clipped: gpd.GeoDataFrame,
) -> Callable[[list[str], bool], Path]:
    def _factory(names: list[str], settings: bool = True) -> Path:
        if settings:
            shutil.copy2(
                Path(model_data_clipped_path, "settings_geom.toml"),
                Path(tmp_path, "settings_geom.toml"),
            )
        # Write the output geometries in the default output directory
        Path(tmp_path, "output").mkdir()
        for name in names:
            exposure_vector_clipped.to_file(Path(tmp_path, "output", f"{name}.fgb"))
        return tmp_path

    return _factory


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
