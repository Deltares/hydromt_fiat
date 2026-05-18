import logging

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Point, box

from hydromt_fiat.utils import DAMAGE, MAX
from hydromt_fiat.workflows import max_value


def test_max_value(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert f"{MAX}_{DAMAGE}_structure" not in exposure_vector_clipped_for_damamge

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_vector_clipped_for_damamge)

    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        country="World",  # Select kwargs
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert f"{MAX}_{DAMAGE}_structure" in exposure_vector_clipped_for_damamge
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 663194


def test_max_value_link(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
    exposure_cost_link: pd.DataFrame,
):
    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        exposure_cost_link=exposure_cost_link,
        country="World",  # Select kwargs
    )

    # Assert the content
    assert len(exposure_vector) == 12
    assert f"{MAX}_{DAMAGE}_structure" in exposure_vector_clipped_for_damamge
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 663194


def test_max_value_link_partial(
    caplog: pytest.LogCaptureFixture,
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
    exposure_cost_link: pd.DataFrame,
):
    caplog.set_level(logging.WARNING)
    # Remove a row from the linking table
    exposure_cost_link.drop(2, inplace=True)  # 2 is industrial
    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_clipped_for_damamge,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        exposure_cost_link=exposure_cost_link,
        country="World",  # Select kwargs
    )

    # Assert the logging
    assert "4 features could not be linked to" in caplog.text

    # Assert the content
    assert len(exposure_vector) == 8
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 822446


def test_max_value_geo_crs(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    geo_input = exposure_vector_clipped_for_damamge.to_crs(4326)
    crs_before = geo_input.crs

    # Call the function
    exposure_vector = max_value(
        exposure_data=geo_input,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers,
        country="World",  # Select kwargs
    )

    # Assert the content
    assert int(exposure_vector[f"{MAX}_{DAMAGE}_structure"].mean()) == 662887
    # CRS must not have been mutated to UTM on the caller's frame
    assert geo_input.crs == crs_before


def test_max_value_no_subtype(
    exposure_vector_data_alt: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers_alt: pd.DataFrame,
):
    # Assert that maximum damage is not already in the dataset
    assert f"{MAX}_{DAMAGE}" not in exposure_vector_data_alt

    # Alterations should be inplace, i.e. id before == id after
    id_before = id(exposure_vector_data_alt)

    # Call the function
    exposure_vector = max_value(
        exposure_data=exposure_vector_data_alt,
        exposure_cost_table=exposure_cost_table,
        exposure_type=DAMAGE,
        vulnerability=vulnerability_identifiers_alt,
        country="World",  # Select kwargs
    )
    id_after = id(exposure_vector)

    # Assert that is was inplace
    assert id_before == id_after

    # Assert the content
    assert f"{MAX}_{DAMAGE}" in exposure_vector_data_alt
    assert int(exposure_vector[f"{MAX}_{DAMAGE}"].mean()) == 1363905


def test_max_value_errors(
    exposure_vector_clipped_for_damamge: gpd.GeoDataFrame,
    exposure_cost_table: pd.DataFrame,
    vulnerability_identifiers: pd.DataFrame,
):
    # Supply none for the cost table
    with pytest.raises(
        ValueError,
        match="Exposure costs table cannot be None",
    ):
        _ = max_value(
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=None,
            exposure_type=DAMAGE,
            vulnerability=vulnerability_identifiers,
        )

    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=r"Select kwargs \(\{'country': 'Unknown'\}\) resulted in no remaining",
    ):
        _ = max_value(
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=exposure_cost_table,
            exposure_type=DAMAGE,
            vulnerability=vulnerability_identifiers,
            country="Unknown",
        )

    # Select kwargs leave no data
    with pytest.raises(
        ValueError,
        match=r"Exposure type \(affected\) not found in vulnerability data",
    ):
        _ = max_value(
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=exposure_cost_table,
            exposure_type="affected",
            vulnerability=vulnerability_identifiers,
            country="World",
        )

    # Exposure cost link table missing columns
    with pytest.raises(
        ValueError,
        match="Cost link table either missing object_type or cost_type",
    ):
        _ = max_value(
            exposure_data=exposure_vector_clipped_for_damamge,
            exposure_cost_table=exposure_cost_table,
            exposure_type=DAMAGE,
            vulnerability=vulnerability_identifiers,
            country="World",
            exposure_cost_link=pd.DataFrame(),
        )


# ---------------------------------------------------------------------------
# New tests: basis auto-detection, alignment & unit conversion, mixed-geometry
# guard
# ---------------------------------------------------------------------------


def _tiny_cost_table(unit: str | None = "$/m2") -> pd.DataFrame:
    # Two rows so the .query(country=='World') step still works.
    df = pd.DataFrame(
        {
            "country": ["World", "Other"],
            "residential": [10.0, 1.0],
        }
    )
    if unit is not None:
        df.attrs["unit"] = unit
    return df


def _tiny_vulnerability() -> pd.DataFrame:
    # No SUBTYPE column → headers = [""], output column is f"max_{exposure_type}".
    return pd.DataFrame(
        {
            "exposure_link": ["residential"],
            "exposure_type": [DAMAGE],
        }
    )


def test_max_value_basis_area_polygon():
    # 10x10 square → area 100 m² → 100 * 10 = 1000
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[box(0, 0, 10, 10)],
        crs=28992,
    )
    result = max_value(
        exposure_data=gdf,
        exposure_cost_table=_tiny_cost_table(),
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert result[f"{MAX}_{DAMAGE}"].iloc[0] == pytest.approx(1000.0)


def test_max_value_basis_length_line():
    # 100 m long line → 100 * 10 = 1000
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[LineString([(0, 0), (100, 0)])],
        crs=28992,
    )
    result = max_value(
        exposure_data=gdf,
        exposure_cost_table=_tiny_cost_table("$/m"),
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert result[f"{MAX}_{DAMAGE}"].iloc[0] == pytest.approx(1000.0)


def test_max_value_basis_object_point():
    # Points + per-object cost (no denominator) → factor 1.0 → result == cost.
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential", "residential"]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs=28992,
    )
    result = max_value(
        exposure_data=gdf,
        exposure_cost_table=_tiny_cost_table("$"),
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert result[f"{MAX}_{DAMAGE}"].tolist() == pytest.approx([10.0, 10.0])


def test_max_value_mixed_geometry_raises():
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential", "residential"]},
        geometry=[box(0, 0, 10, 10), Point(20, 20)],
        crs=28992,
    )
    with pytest.raises(ValueError, match="Mixed geometry types"):
        _ = max_value(
            exposure_data=gdf,
            exposure_cost_table=_tiny_cost_table(),
            exposure_type=DAMAGE,
            vulnerability=_tiny_vulnerability(),
            country="World",
        )


def test_max_value_unit_conversion(caplog: pytest.LogCaptureFixture):
    # 1 km × 1 km polygon (area = 1e6 m² = 1 km²). Cost cell == 10.
    # $/m2 → factor 1e6 m² → result 1e7.
    # $/km2 → factor 1 km² → result 10.
    caplog.set_level(logging.WARNING)
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[box(0, 0, 1000, 1000)],
        crs=28992,
    )
    result_m2 = max_value(
        exposure_data=gdf.copy(),
        exposure_cost_table=_tiny_cost_table("$/m2"),
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert result_m2[f"{MAX}_{DAMAGE}"].iloc[0] == pytest.approx(1e7)

    caplog.clear()
    result_km2 = max_value(
        exposure_data=gdf.copy(),
        exposure_cost_table=_tiny_cost_table("$/km2"),
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert result_km2[f"{MAX}_{DAMAGE}"].iloc[0] == pytest.approx(10.0)
    assert "Converting geometry to 'km2'" in caplog.text


def test_max_value_unit_default_when_attr_missing():
    # No attrs['unit'] → fall back to "$/m2" semantics (legacy default).
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[box(0, 0, 10, 10)],
        crs=28992,
    )
    cost = _tiny_cost_table(unit=None)
    assert "unit" not in cost.attrs
    result = max_value(
        exposure_data=gdf,
        exposure_cost_table=cost,
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert result[f"{MAX}_{DAMAGE}"].iloc[0] == pytest.approx(1000.0)


def test_max_value_no_denominator_polygon():
    # Polygon + per-object cost is valid → factor 1.0, ignores area.
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[box(0, 0, 10, 10)],
        crs=28992,
    )
    result = max_value(
        exposure_data=gdf,
        exposure_cost_table=_tiny_cost_table("$"),
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert result[f"{MAX}_{DAMAGE}"].iloc[0] == pytest.approx(10.0)


def test_max_value_alignment_errors():
    poly = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[box(0, 0, 10, 10)],
        crs=28992,
    )
    line = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[LineString([(0, 0), (100, 0)])],
        crs=28992,
    )
    point = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[Point(0, 0)],
        crs=28992,
    )

    # Polygon with length denominator → raise
    with pytest.raises(ValueError, match="not an area unit"):
        max_value(
            exposure_data=poly,
            exposure_cost_table=_tiny_cost_table("$/m"),
            exposure_type=DAMAGE,
            vulnerability=_tiny_vulnerability(),
            country="World",
        )
    # Line with area denominator → raise
    with pytest.raises(ValueError, match="not a length unit"):
        max_value(
            exposure_data=line,
            exposure_cost_table=_tiny_cost_table("$/m2"),
            exposure_type=DAMAGE,
            vulnerability=_tiny_vulnerability(),
            country="World",
        )
    # Point with any denominator → raise
    with pytest.raises(ValueError, match="Point geometry but cost-cell unit"):
        max_value(
            exposure_data=point,
            exposure_cost_table=_tiny_cost_table("$/m2"),
            exposure_type=DAMAGE,
            vulnerability=_tiny_vulnerability(),
            country="World",
        )


def test_max_value_multi_utm_zone_warning(caplog: pytest.LogCaptureFixture):
    # Two small polygons in WGS84 spanning multiple UTM zones in the
    # northern hemisphere: UTM 30N (lon=-1) and UTM 33N (lon=15).
    caplog.set_level(logging.WARNING)
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential", "residential"]},
        geometry=[
            box(-1.0, 50.0, -0.99, 50.01),
            box(15.0, 50.0, 15.01, 50.01),
        ],
        crs=4326,
    )
    _ = max_value(
        exposure_data=gdf,
        exposure_cost_table=_tiny_cost_table(),
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert "span more than one UTM zone" in caplog.text


def test_max_value_no_mutation_of_input_crs():
    # Geographic input → workflow internally reprojects to UTM, but the
    # caller's GeoDataFrame must retain its original CRS afterwards.
    gdf = gpd.GeoDataFrame(
        {"object_type": ["residential"]},
        geometry=[box(4.0, 52.0, 4.001, 52.001)],
        crs=4326,
    )
    crs_before = gdf.crs
    _ = max_value(
        exposure_data=gdf,
        exposure_cost_table=_tiny_cost_table(),
        exposure_type=DAMAGE,
        vulnerability=_tiny_vulnerability(),
        country="World",
    )
    assert gdf.crs == crs_before
    # Sanity: a non-zero area must have been computed (geo CRS handled correctly)
    assert gdf[f"{MAX}_{DAMAGE}"].iloc[0] > 0
    assert np.isfinite(gdf[f"{MAX}_{DAMAGE}"].iloc[0])
