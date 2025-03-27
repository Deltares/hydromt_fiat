import xarray as xr
from hydromt import DataCatalog

from hydromt_fiat.workflows import hazard_data


def test_parse_hazard_data(build_data_catalog, build_region_gdf):
    # test hazard risk
    hazard_files = ["flood_event_highres"]
    datacatalog = DataCatalog(build_data_catalog)
    ds = hazard_data(
        data_catalog=datacatalog,
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

    # Test hazard event
    hazard_files = ["flood_event"]
    ds = hazard_data(
        data_catalog=datacatalog,
        hazard_fnames=hazard_files,
        hazard_type="flooding",
        risk=False,
        region=build_region_gdf,
    )
    assert isinstance(ds, xr.Dataset)
    assert ds.analysis == "event"
    assert ds.name == ["flood_event"]
    assert "return_period" not in ds.attrs.keys()
