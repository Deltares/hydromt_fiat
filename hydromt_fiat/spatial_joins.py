import os
from typing import Any, Union

import tomli
import tomli_w
from hydromt_fiat.interface.spatial_joins import ISpatialJoins, SpatialJoinsModel


class SpatialJoins(ISpatialJoins):
    attrs: SpatialJoinsModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create SpatialJoins from toml file"""

        obj = SpatialJoins()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SpatialJoinsModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create SpatialJoins from object, e.g. when initialized from GUI"""

        obj = SpatialJoins()
        obj.attrs = SpatialJoinsModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save SpatialJoins to a toml file"""
        if not os.path.exists(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)
