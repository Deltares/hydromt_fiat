import os
from abc import ABC, abstractmethod
from typing import Any, Union, Optional
from pydantic import BaseModel


class SpatialJoinModel(BaseModel):
    """
    Represents a spatial join model.

    Attributes:
        name (Optional[str]): The name of the model (optional).
        file (str): The file associated with the model.
        field_name (str): The field name used for the spatial join.
    """

    name: Optional[str] = None
    file: str
    field_name: str


class EquityModel(BaseModel):
    census_data: str
    percapitaincome_label: Optional[str] = "PerCapitaIncome"
    totalpopulation_label: Optional[str] = "TotalPopulation"


class AggregationModel(SpatialJoinModel):
    equity: Optional[EquityModel] = None


class SpatialJoinsModel(BaseModel):
    """BaseModel describing the expected variables and data types of a Delft-FIAT spatial_joins.toml"""

    aggregation_areas: Optional[list[AggregationModel]] = None
    additional_attributes: Optional[list[SpatialJoinModel]] = None


class ISpatialJoins(ABC):
    attrs: SpatialJoinsModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Get Delft-FIAT spatial joins attributes from a Delft-FIAT spatial_joins.toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """Get Delft-FIAT spatial joins attributes from a dictionary."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Delft-FIAT spatial joins attributes to a Delft-FIAT spatial_joins.toml file."""
