import os
from typing import Union

import tomli
import tomli_w
from hydromt_fiat.interface.config import IConfig


class Config(IConfig):
    def load_file(self, filepath: Union[str, os.PathLike]):
        """create Projection from toml file"""

        with open(filepath, mode="rb") as fp:
            config = tomli.load(fp)

        return config

    @staticmethod
    def save(config, filepath: Union[str, os.PathLike]):
        """save Projection to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(config, f)
