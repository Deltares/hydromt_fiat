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
