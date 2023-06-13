from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict, Union

from pydantic import BaseModel


class ExtractionMethod(str, Enum):
    centroid = "centroid"
    area = "area"


class Units(Enum):
    m = "meter"
    feet = "feet"


class Category(Enum):
    exposure = "exposure"
    hazard = "hazard"
    vulnerability = "vulnerability"


class Meta(TypedDict):
    category: Category


class DataCatalogEntry(BaseModel):
    path: Union[str, Path]
    data_type: str
    driver: str
    crs: Optional[str]
    translation_fn: Optional[str]
    meta: Meta
