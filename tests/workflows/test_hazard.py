import xarray as xr
from hydromt import DataCatalog

from hydromt_fiat.workflows import parse_hazard_data


def test_parse_hazard_data(build_data_catalog):
    # test hazard risk
    hazard_files = ["flood_50000"]
    datacatalog = DataCatalog(build_data_catalog)
    ds = parse_hazard_data(
        data_catalog=datacatalog,
        hazard_fnames=hazard_files,
        hazard_type="flooding",
        return_periods=[50000],
        risk=True,
    )
    assert isinstance(ds, xr.Dataset)
    assert ds.analysis == "risk"
    assert ds.name == ["flood_50000"]
    assert ds.return_period == [50000]

    # Test hazard event
    hazard_files = ["flood_event"]
    ds = parse_hazard_data(
        data_catalog=datacatalog,
        hazard_fnames=hazard_files,
        hazard_type="flooding",
        risk=False,
    )
    assert isinstance(ds, xr.Dataset)
    assert ds.analysis == "event"
    assert ds.name == ["flood_event"]
    assert "return_period" not in ds.attrs.keys()
