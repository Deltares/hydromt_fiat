from pathlib import Path
from typing import Union

from pydantic import BaseModel

from hydromt_fiat.api.data_types import ExtractionMethod, Units

# filepath = Path(__file__).parent / "exposure.toml"
# obj = ConfigHandler.load_file(filepath)


# print(time.time_ns())
# a = ExposureViewModel()
# a.exposure_model.asset_locations = "nsi"
# print(a)


class ExposureVectorIni(BaseModel):
    asset_locations: Union[str, Path]
    occupancy_type: Union[str, Path]
    max_potential_damage: Union[int, Path]
    ground_floor_height: Union[int, Path]
    gfh_units: Units
    extraction_method: ExtractionMethod


a = ExposureVectorIni.parse_obj({})

print(a)
