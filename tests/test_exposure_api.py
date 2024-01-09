from pathlib import Path
import pytest
from hydromt_fiat.api.hydromt_fiat_vm import HydroMtViewModel


@pytest.mark.skip(reason="not finished")
def test_hydromt_fiat_vm():
    path_to_database = Path(__file__).parents[1] / "hydromt_fiat" / "data"
    path_to_datacatalog = str(
        Path(__file__).parents[1] / "hydromt_fiat" / "data" / "data_catalog.yml"
    )
    view_model = HydroMtViewModel(path_to_database, path_to_datacatalog)

    view_model.build_config_yaml()
    view_model.save_data_catalog()

    print("exit")
