from pathlib import Path
from typing import Dict, NewType, Optional, TypeAlias, Union

import tomli
from pydantic import BaseModel

area = NewType("area", str)
centroid = NewType("centroid", str)
meter = NewType("m", str)
feet = NewType("feet", str)

ExtractionMethod: TypeAlias = area | centroid
Units: TypeAlias = meter | feet


class Hazard(BaseModel):
    hazard_map: Union[str, Path]
    hazard_type: str
    return_period: Optional[Union[int, None]] = None
    crs: Optional[str] = None
    no_data: Optional[int] = -9999
    var: Optional[Union[str, None]] = None
    chunks: Optional[Union[int, str]] = "auto"


class Vulnerability(BaseModel):
    vulnerability_fns: Union[str, Path]
    link_table: Union[str, Path]
    units: Units


class Exposure(BaseModel):
    asset_locations: Union[str, Path]
    occupancy_type: Union[str, Path]
    max_potential_damage: Union[int, Path]
    ground_floor_height: Union[int, Path]
    gfh_units: Units
    extraction_method: ExtractionMethod


class MBuilderComponent:
    attrs: Exposure | Vulnerability | Hazard

    _clc = {"exposure": Exposure, "vulnerability": Vulnerability, "hazard": Hazard}

    @staticmethod
    def load_file(filepath: Path, component_type: str):
        try:
            obj = MBuilderComponent()
            with open(filepath, "rb") as f:
                toml_dict = tomli.load(f)
                obj.attrs = obj._clc[component_type].parse_obj(toml_dict)

            return obj

        except Exception:
            ...

        ...

    def load_dict(self, model_config: Dict):
        ...

    def save_dict(self, filepath: Path):
        ...
