from pathlib import Path
from typing import Any, Dict, NewType, Optional, TypeAlias, Union

import tomli
import tomli_w
from pydantic import BaseModel

area = NewType("area", str)
centroid = NewType("centroid", str)
meter = NewType("m", str)
feet = NewType("feet", str)

ExtractionMethod: TypeAlias = area | centroid
Units: TypeAlias = meter | feet


class Config(BaseModel):
    output_dir: Path
    crs: str


class Hazard(BaseModel):
    hazard_map_fn: Union[str, Path]
    hazard_type: str
    return_period: Optional[Union[int, None]] = None
    crs: Optional[str] = None
    no_data: Optional[int] = -9999
    var: Optional[Union[str, None]] = None
    chunks: Optional[Union[int, str]] = "auto"


class Vulnerability(BaseModel):
    vulnerability_fn: Union[str, Path]
    link_table: Union[str, Path]
    units: Units


class ExposureVector(BaseModel):
    asset_locations: Union[str, Path]
    occupancy_type: Union[str, Path]
    max_potential_damage: Union[int, Path]
    ground_floor_height: Union[int, Path]
    gfh_units: Units
    extraction_method: ExtractionMethod


class ExposureGrid(BaseModel):
    ...


class HydroMTConfig(BaseModel):
    setup_config: Config
    setup_hazard: Hazard
    setup_vulnerability: Vulnerability
    setup_exposure_vector: ExposureVector


class MBuilderComponent:
    # _component_table = {
    #     "exposure": Exposure,
    #     "vulnerability": Vulnerability,
    #     "hazard": Hazard,
    # }

    def __init__(self):
        self.attrs: HydroMTConfig

    @staticmethod
    def load_file(filepath: Path | str) -> object:
        try:
            obj = MBuilderComponent()
            with open(filepath, "rb") as f:
                toml_dict = tomli.load(f)
                obj.attrs = HydroMTConfig.parse_obj(toml_dict)
                return obj
        except FileNotFoundError as err:
            print(f"Error no {err.errno}: {err.strerror} {err.filename}")

    @staticmethod
    def load_dict(model_dict: Dict[str, Any]) -> object:
        try:
            MBuilderComponent()
            # obj.attrs = HydroMTConfig
            # return obj

        except Exception:
            ...

    def save(self, filepath: Path) -> None:
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(), f)
