import numpy as np
import xarray as xr

from hydromt_fiat.workflows import hazard_data


def test_hazard_data_risk(build_region_gdf, data_catalog):
    # test hazard risk
    hazard_files = ["flood_event_highres"]
    ds = hazard_data(
        grid_like=None,
        data_catalog=data_catalog,
        hazard_fnames=hazard_files,
        hazard_type="flooding",
        return_periods=[50000],
        risk=True,
        region=build_region_gdf,
    )
    assert isinstance(ds, xr.Dataset)
    assert ds.analysis == "risk"
    assert ds.name == ["flood_event_highres"]
    assert ds.return_period == [50000]


def test_hazard_data_event(build_region_gdf, data_catalog):
    # Test hazard event
    hazard_files = ["flood_event"]
    ds = hazard_data(
        grid_like=None,
        data_catalog=data_catalog,
        hazard_fnames=hazard_files,
        hazard_type="flooding",
        risk=False,
        region=build_region_gdf,
    )
    assert isinstance(ds, xr.Dataset)
    assert ds.analysis == "event"
    assert ds.name == ["flood_event"]
    assert "return_period" not in ds.attrs.keys()


def test_hazard_data_unit_default(
    build_region_gdf,
    data_catalog,
):
    hazard_files = ["flood_event"]
    ds = hazard_data(
        grid_like=None,
        data_catalog=data_catalog,
        hazard_fnames=hazard_files,
        hazard_type="flooding",
        region=build_region_gdf,
    )

    avg_level = ds.flood_event.mean().values
    assert np.isclose(avg_level, 1.2019)


def test_hazard_data_unit_differ(build_region_gdf, data_catalog, caplog):
    hazard_files = ["flood_event"]
    # Suppose it's in a different unit
    ds = hazard_data(
        grid_like=None,
        data_catalog=data_catalog,
        hazard_fnames=hazard_files,
        hazard_type="flooding",
        region=build_region_gdf,
        unit="ft",
    )

    avg_level_ft = ds.flood_event.mean().values
    assert (
        "Given unit (ft) does not match the standard unit (m) for length" in caplog.text
    )
    assert np.isclose(avg_level_ft, 0.366337)
