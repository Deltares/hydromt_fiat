import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import pandas as pd
import pytest
from hydromt.model import ModelRoot

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ExposureGeomsComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.utils import (
    DAMAGE,
    EXPOSURE,
    EXPOSURE_GEOM,
    FILE,
    FN,
    GEOM,
    MODEL_TYPE,
    SUBTYPE,
)


def test_exposure_geom_component_empty(mock_model: MagicMock):
    component = ExposureGeomsComponent(model=mock_model)

    assert component._filename == f"{EXPOSURE}/{{name}}.fgb"
    assert len(component.data) == 0
    assert isinstance(component.data, dict)


def test_exposure_geom_component_read(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    component = ExposureGeomsComponent(model=mock_model_config)

    assert component._data is None
    component.data

    assert isinstance(component._data, dict)
    assert len(component._data) == 1
    assert "buildings" in component.data


def test_exposure_geom_component_read_sig(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    component = ExposureGeomsComponent(model=mock_model_config)

    assert component._data is None
    component.read(f"{EXPOSURE}/{{name}}.fgb")

    assert len(component._data) == 2


def test_exposure_geom_component_read_csv(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_vector_clipped_csv_path: Path,
):
    type(mock_model_config).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="r"),
    )
    component = ExposureGeomsComponent(model=mock_model_config)

    assert component._data is None
    component.read(filename="{name}.fgb")

    assert len(component._data) == 1
    assert len(component.data["foo"]) == 12
    assert "object_id" in component.data["foo"].columns
    assert "ref" in component.data["foo"].columns


def test_exposure_geom_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    component = ExposureGeomsComponent(model=mock_model_config)
    component._data = {
        "buildings": exposure_vector_clipped,
        "buildings2": exposure_vector_clipped,
    }

    component.write()

    assert Path(tmp_path, component._filename.format(name="buildings")).is_file()
    assert Path(tmp_path, component._filename.format(name="buildings2")).is_file()

    geom_cfg = mock_model_config.config.get(EXPOSURE_GEOM)
    assert len(geom_cfg) == 2
    assert geom_cfg[0][FILE] == Path(tmp_path, f"{EXPOSURE}/buildings.fgb")


def test_exposure_geom_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_vector_clipped: gpd.GeoDataFrame,
):
    component = ExposureGeomsComponent(model=mock_model_config)
    component._data = {
        "buildings": exposure_vector_clipped,
    }

    component.write("other/{name}.fgb")

    assert Path(tmp_path, "other", "buildings.fgb").is_file()


def test_exposure_geom_component_write_warnings(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    mock_model: MagicMock,
):
    caplog.set_level(logging.DEBUG)
    type(mock_model).root = PropertyMock(
        side_effect=lambda: ModelRoot(tmp_path, mode="w"),
    )
    component = ExposureGeomsComponent(model=mock_model)

    component.write()
    assert "No geoms data found, skip writing." in caplog.text

    component.set(gpd.GeoDataFrame(), name="empty_ds")
    component.write()
    assert "empty_ds is empty. Skipping..." in caplog.text


def test_exposure_geom_component_setup(
    model_exposure_setup: FIATModel,
    vulnerability_identifiers_path: Path,
):
    component = ExposureGeomsComponent(model=model_exposure_setup)

    assert len(component.data) == 0
    assert EXPOSURE not in component.model.config.data

    component.setup(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
        vulnerability_link_fname=vulnerability_identifiers_path,
    )

    assert len(component.data) == 1
    assert "buildings" in component.data
    assert len(component.data["buildings"]) != 0
    assert f"{FN}_{DAMAGE}_structure" in component.data["buildings"].columns
    # The link rows are appended to the shared vulnerability identifiers table
    identifiers = model_exposure_setup.vulnerability.data.identifiers
    assert "buildings" in identifiers["exposure_geom"].unique()

    assert component.model.config.get(MODEL_TYPE) == GEOM


def test_exposure_geom_component_setup_errors(
    model: FIATModel,
    vulnerability_identifiers_path: Path,
):
    component = ExposureGeomsComponent(model=model)

    with pytest.raises(
        MissingRegionError,
        match="Region is None -> use 'setup_region' before this method",
    ):
        component.setup(
            exposure_fname="bag",
            exposure_type_column="gebruiksdoel",
            exposure_link_fname="bag_link",
            vulnerability_link_fname=vulnerability_identifiers_path,
        )


def test_exposure_geom_component_setup_no_vulnerability(
    model_with_region: FIATModel,
    vulnerability_identifiers_path: Path,
):
    component = ExposureGeomsComponent(model=model_with_region)

    with pytest.raises(RuntimeError, match="No vulnerability curves"):
        component.setup(
            exposure_fname="buildings",
            exposure_type_column="gebruiksdoel",
            exposure_link_fname="buildings_link",
            vulnerability_link_fname=vulnerability_identifiers_path,
        )


def test_exposure_geom_component_setup_deferred_link(
    model_exposure_setup: FIATModel,
    vulnerability_identifiers_path: Path,
):
    """Calling setup without vulnerability_link_fname stores unlinked exposure,
    then setup_link_vulnerability applies the link in a separate step."""
    component = ExposureGeomsComponent(model=model_exposure_setup)

    # Step 1: load exposure without linking
    component.setup(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
    )
    assert "buildings" in component.data
    assert f"{FN}_{DAMAGE}_structure" not in component.data["buildings"].columns
    # identifiers untouched
    assert model_exposure_setup.vulnerability.data.identifiers.empty

    # Step 2: link in a separate call
    component.setup_link_vulnerability(
        exposure_name="buildings",
        vulnerability_link_fname=vulnerability_identifiers_path,
    )
    assert f"{FN}_{DAMAGE}_structure" in component.data["buildings"].columns
    ids = model_exposure_setup.vulnerability.data.identifiers
    assert "buildings" in ids["exposure_geom"].unique()


def test_exposure_geom_component_setup_link_vulnerability_double_link(
    model_exposure_setup: FIATModel,
    vulnerability_identifiers_path: Path,
):
    """Re-linking the same dataset without re-running setup raises."""
    component = ExposureGeomsComponent(model=model_exposure_setup)
    component.setup(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
        vulnerability_link_fname=vulnerability_identifiers_path,
    )

    with pytest.raises(RuntimeError, match="already linked"):
        component.setup_link_vulnerability(
            exposure_name="buildings",
            vulnerability_link_fname=vulnerability_identifiers_path,
        )


def test_exposure_geom_component_setup_link_vulnerability_unknown_exposure(
    model_exposure_setup: FIATModel,
    vulnerability_identifiers_path: Path,
):
    """setup_link_vulnerability on a name that hasn't been setup raises."""
    component = ExposureGeomsComponent(model=model_exposure_setup)
    with pytest.raises(RuntimeError, match="already present geometries"):
        component.setup_link_vulnerability(
            exposure_name="never_setup",
            vulnerability_link_fname=vulnerability_identifiers_path,
        )


def test_exposure_geom_component_setup_max(
    model_exposure_setup: FIATModel,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    component = ExposureGeomsComponent(model=model_exposure_setup)
    component.set(exposure_vector_clipped_for_damamge, name="buildings")
    model_exposure_setup.vulnerability.append_identifiers(
        name="buildings", link=vulnerability_identifiers
    )

    assert "max_damage_structure" not in component.data["buildings"].columns

    component.setup_max_damage(
        exposure_name="buildings",
        exposure_type="damage",
        exposure_cost_table_fname="jrc_damage",
        country="World",
    )

    assert "max_damage_structure" in component.data["buildings"].columns


def test_exposure_geom_component_setup_max_link(
    model_exposure_setup: FIATModel,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_link_path: Path,
    vulnerability_identifiers: pd.DataFrame,
):
    component = ExposureGeomsComponent(model=model_exposure_setup)
    component.set(exposure_vector_clipped_for_damamge, name="buildings")
    model_exposure_setup.vulnerability.append_identifiers(
        name="buildings", link=vulnerability_identifiers
    )

    assert "max_damage_structure" not in component.data["buildings"].columns

    component.setup_max_damage(
        exposure_name="buildings",
        exposure_type="damage",
        exposure_cost_table_fname="jrc_damage",
        exposure_cost_link_fname=exposure_cost_link_path,
        country="World",
    )

    assert "max_damage_structure" in component.data["buildings"].columns


def test_exposure_geom_component_setup_max_missing_link(
    model_exposure_setup: FIATModel,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
):
    component = ExposureGeomsComponent(model=model_exposure_setup)
    component.set(exposure_vector_clipped_for_damamge, name="buildings")

    with pytest.raises(KeyError, match="No vulnerability identifiers"):
        component.setup_max_damage(
            exposure_name="buildings",
            exposure_type="damage",
            exposure_cost_table_fname="jrc_damage",
            country="World",
        )


def test_exposure_geom_component_update_cols(
    model_with_region: FIATModel,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
):
    component = ExposureGeomsComponent(model=model_with_region)
    component.set(exposure_vector_clipped_for_damamge, name="bag")

    assert "foo" not in component.data["bag"].columns

    component.update_column(
        exposure_name="bag",
        columns=["foo"],
        values=0,
    )

    assert "foo" in component.data["bag"].columns

    assert "ref" not in component.data["bag"].columns
    assert "method" not in component.data["bag"].columns

    component.update_column(
        exposure_name="bag",
        columns=["ref", "method"],
        values=[0, "centroid"],
    )

    assert "ref" in component.data["bag"].columns
    assert "method" in component.data["bag"].columns


def test_exposure_geom_component_setup_collision_isolation(
    tmp_path: Path,
    model_with_region: FIATModel,
    vulnerability_curves: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    """Regression: a road link table whose exposure_link='residential' must NOT pull
    in structure/content curves from a separate building link table."""
    model_with_region.vulnerability._set_curves(vulnerability_curves)
    component = ExposureGeomsComponent(model=model_with_region)

    # Pretend we only ever pass a link with the 'structure' subtype (buildings).
    structure_only = vulnerability_identifiers[
        vulnerability_identifiers[SUBTYPE] == "structure"
    ]
    structure_path = Path(tmp_path, "structure_only_link.csv")
    structure_only.to_csv(structure_path, index=False)

    component.setup(
        exposure_fname="buildings",
        exposure_type_column="gebruiksdoel",
        exposure_link_fname="buildings_link",
        vulnerability_link_fname=structure_path,
    )

    cols = component.data["buildings"].columns
    assert f"{FN}_{DAMAGE}_structure" in cols
    # Critical: no content or road column leaked in from other scopes
    assert f"{FN}_{DAMAGE}_content" not in cols
    assert f"{FN}_{DAMAGE}_road" not in cols
