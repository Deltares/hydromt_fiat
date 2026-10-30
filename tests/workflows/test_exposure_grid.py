import logging
import re

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from hydromt_fiat.utils import (
    CURVE,
    EXPOSURE__TYPE,
    FN__CURVE,
    OBJECT__TYPE,
    VALUE,
)
from hydromt_fiat.workflows import (
    exposure_grid_categorized_setup,
    exposure_grid_category_values,
    exposure_grid_default_setup,
    exposure_grid_from_geometries,
)


def test_exposure_grid_default_setup(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_link: pd.DataFrame,
):
    # Call the function
    ds = exposure_grid_default_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_link,
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert len(ds.data_vars) == 1
    assert ds.industrial_content.attrs.get(FN__CURVE) == "in2"


def test_exposure_grid_default_setup_linking(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_link: pd.DataFrame,
    exposure_grid_link: pd.DataFrame,
):
    # Call the function, bit stupid is this table just returns the same
    ds = exposure_grid_default_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_link,
        exposure_link=exposure_grid_link,
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert ds.industrial_content.attrs.get(FN__CURVE) == "in2"


def test_exposure_grid_default_setup_link_no(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_link: pd.DataFrame,
):
    # Call the function, bit stupid is this table just returns the same
    ds = exposure_grid_default_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_link,
        exposure_link=pd.DataFrame(data={EXPOSURE__TYPE: [], OBJECT__TYPE: []}),
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert ds.industrial_content.attrs.get(FN__CURVE) == "in2"


def test_exposure_grid_default_setup_alt(
    caplog: pytest.LogCaptureFixture,
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_link_alt: pd.DataFrame,
):
    caplog.set_level(logging.WARNING)
    # Call the function, shouldn't be able to link to the vulnerability
    ds = exposure_grid_default_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_link_alt,
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert len(ds.data_vars) == 0
    # Assert the logging
    assert (
        "Couldn't link 'industrial_content' to vulnerability, skipping..."
        in caplog.text
    )


def test_exposure_grid_default_setup_alt_link(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_link_alt: pd.DataFrame,
):
    # Call the function, shouldn't be able to link to the vulnerability
    ds = exposure_grid_default_setup(
        grid_like=None,
        exposure_data={"industrial_content": exposure_grid_data_ind},
        vulnerability=vulnerability_link_alt,
        exposure_link=pd.DataFrame(
            data={
                EXPOSURE__TYPE: ["industrial_content"],
                OBJECT__TYPE: ["industrial"],
            }
        ),
    )

    # Assert the output
    assert isinstance(ds, xr.Dataset)
    assert len(ds.data_vars) == 1


def test_exposure_grid_default_setup_errors(
    exposure_grid_data_ind: xr.DataArray,
    vulnerability_link: pd.DataFrame,
):
    # Assert an error on the missing necessary columns
    with pytest.raises(
        ValueError,
        match="Missing column, 'exposure_type' in exposure grid linking table",
    ):
        # Call the function
        _ = exposure_grid_default_setup(
            grid_like=None,
            exposure_data={"industrial_content": exposure_grid_data_ind},
            vulnerability=vulnerability_link,
            exposure_link=pd.DataFrame(),
        )


def test_exposure_grid_categorized_setup(exposure_grid: xr.Dataset):
    # Call the function
    out = exposure_grid_categorized_setup(
        exposure_data=exposure_grid["buildings"],
        vulnerability=pd.DataFrame({CURVE: [1, 2, 3, 4]}),
        name="foo",
    )

    # Assert the output
    assert "foo" in out.data_vars
    np.testing.assert_array_equal(
        np.unique(out["foo"]),
        desired=[0, 1, 2, 3, 4],
    )
    assert out.raster.shape == exposure_grid.raster.shape


def test_exposure_grid_categorized_setup_warnings(
    caplog: pytest.LogCaptureFixture,
    exposure_grid: xr.Dataset,
):
    caplog.set_level(logging.INFO)
    # Call the function
    _ = exposure_grid_categorized_setup(
        exposure_data=exposure_grid["buildings"],
        vulnerability=pd.DataFrame({CURVE: [1, 2, 4]}),
        name="foo",
    )

    assert "The following categories have no correspoding curve: [3]" in caplog.text


def test_exposure_grid_category_values(
    exposure_grid: xr.Dataset,
    exposure_grid_cat_table: pd.DataFrame,
):
    # Call the function
    out = exposure_grid_category_values(
        exposure_data=exposure_grid["buildings"],
        table=exposure_grid_cat_table,
        index_name=VALUE,
    )

    # Assert the output
    assert "buildings_cat" in out.dims
    assert "buildings_structure" in out.data_vars
    assert "buildings_content" in out.data_vars
    np.testing.assert_array_equal(
        out["buildings_cat"].values,
        [0, 1, 2, 3, 4],
    )
    np.testing.assert_array_equal(
        out["buildings_structure"].values, [0, 294, 319, 217, 277]
    )


def test_exposure_grid_category_values_select(
    exposure_grid: xr.Dataset,
    exposure_grid_cat_table: pd.DataFrame,
):
    # Call the function
    out = exposure_grid_category_values(
        exposure_data=exposure_grid["buildings"],
        table=exposure_grid_cat_table,
        index_name=VALUE,
        columns="structure",
    )

    # Assert the output
    assert "buildings_cat" in out.dims
    assert "buildings_structure" in out.data_vars
    assert "buildings_content" not in out.data_vars


def test_exposure_grid_category_values_no_table(
    exposure_grid: xr.Dataset,
):
    # Call the function
    out = exposure_grid_category_values(
        exposure_data=exposure_grid["buildings"],
        default=50,
    )

    # Assert the output
    assert "buildings_cat" in out.dims
    assert "buildings_value" in out.data_vars
    np.testing.assert_array_equal(
        out["buildings_value"].values,
        [0, 50, 50, 50, 50],
    )


def test_exposure_grid_category_values_errors(
    exposure_grid: xr.Dataset,
    exposure_grid_cat_table: pd.DataFrame,
):
    # Call the function with a random dataarray
    # This will not have the categories attributes
    with pytest.raises(
        AttributeError,
        match="'categories' attribute should be present in the exposure DataArray",
    ):
        _ = exposure_grid_category_values(
            exposure_data=xr.DataArray(),
        )

    # Call the function with a column that is not available
    with pytest.raises(
        ValueError,
        match=re.escape("['foo'] columns no available in provided table data"),
    ):
        _ = exposure_grid_category_values(
            exposure_data=exposure_grid["buildings"],
            table=exposure_grid_cat_table,
            index_name=VALUE,
            columns=["foo"],
        )


def test_exposure_grid_from_geometries(
    exposure_vector: gpd.GeoDataFrame,
    exposure_grid: xr.Dataset,
    vulnerability_link: pd.DataFrame,
):
    # Call the function
    out = exposure_grid_from_geometries(
        exposure_data=exposure_vector,
        column="max_damage_structure",
        curve="commercial_structure",
        vulnerability=vulnerability_link,
        ds_like=exposure_grid,
    )

    # Assert the output
    assert out.raster.shape == exposure_grid.raster.shape
    assert out.raster.nodata == -9999
    np.testing.assert_almost_equal(
        np.nanmean(out.raster.mask_nodata()), 959943, decimal=0
    )
    assert out.attrs["fn_curve"] == "cm1"


def test_exposure_grid_from_geometries_errors(
    exposure_vector: gpd.GeoDataFrame,
    exposure_grid: xr.Dataset,
    vulnerability_link: pd.DataFrame,
):
    # Call the function with a nonsense vulnerability curve identifier
    with pytest.raises(
        RuntimeError,
        match="Could not resolve vulnerability curve: foo",
    ):
        _ = exposure_grid_from_geometries(
            exposure_data=exposure_vector,
            column="max_damage_structure",
            curve="foo",
            vulnerability=vulnerability_link,
            ds_like=exposure_grid,
        )
