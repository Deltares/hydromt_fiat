"""Main module."""

from logging import Logger, getLogger
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from hydromt import Model
from hydromt.io.readers import read_toml
from hydromt.model.components.config import ConfigComponent
from hydromt.model.components.grid import GridComponent
from hydromt.model.components.vector import VectorComponent

logger: Logger = getLogger(__name__)


class FIATModel(Model):
    """_summary_."""

    name: str = "FIAT_model"
    _MODEL_VERSION = "v1.0"

    def __init__(
        self,
        root: Optional[str] = None,
        *,
        components: Optional[Dict[str, Any]] = None,
        mode: str = "w",
        config_fn: Optional[str] = None,
        data_libs: Optional[Union[List, str]] = None,
        region_component: Optional[str] = None,
        **catalog_keys,
    ):
        components = {
            "config": ConfigComponent,
            "grid": GridComponent,
            "vector": VectorComponent,
        }
        super().__init__(
            root=root,
            components=components,
            mode=mode,
            data_libs=data_libs,
            region_component=region_component,
            **catalog_keys,
        )
        config = ConfigComponent(self, filename=config_fn)
        self.add_component(name="config", component=config)

    def setup_global_settings(
        self,
        crs: Optional[Union[str, int]] = None,
        gdal_cache: Optional[int] = None,
        keep_temp_files: Optional[bool] = None,
        thread: Optional[int] = None,
        chunk: Optional[List[int]] = None,
    ) -> None:
        """To setup Delft-FIAT global settings.

        Parameters
        ----------
        crs : Optional[str], optional
            _description_, by default None
        gdal_cache : Optional[int], optional
            _description_, by default None
        keep_temp_files : Optional[bool], optional
            _description_, by default None
        thread : Optional[int], optional
            _description_, by default None
        chunk : Optional[List[int]], optional
            _description_, by default None
        """
        config = self.get_component(name="config")
        if crs:
            config.set("global.crs", f"EPSG:{crs}")
        if gdal_cache:
            config.set("global.gdal_cache", gdal_cache)
        if keep_temp_files:
            config.set("global.keep_temp_files", keep_temp_files)
        if thread:
            config.set("global.thread", thread)
        if chunk:
            config.set("global.grid.chunk", chunk)

    def setup_output(
        self,
        output_dir: str = "output",
        output_csv_name: str = "output.csv",
        output_vector_name: Union[str, List[str]] = "spatial.gpkg",
    ) -> None:
        """To setup Delft-FIAT output folder and files.

        Parameters
        ----------
        output_dir : str, optional
            The name of the output directory, by default "output".
        output_csv_name : str, optional
            The name of the output csv file, by default "output.csv".
        output_vector_name : Union[str, List[str]], optional
            The name of the output vector file, by default "spatial.gpkg".
        """
        config = self.get_component("config")
        config.set("output_path", output_dir)
        config.set("output.csv.name", output_csv_name)

        if isinstance(output_vector_name, str):
            output_vector_name = [output_vector_name]
        for i, name in enumerate(output_vector_name):
            config.set(f"output.geom.name{str(i+1)}", name)

    def setup_exposure_grid(self):
        pass

    def setup_exposure_vector(self):
        pass

    @staticmethod
    def from_toml(path: Path) -> "FIATModel":
        """Construct a model with the components and other init arguments in the toml file located at `path`."""
        file_contents = read_toml(path)
        return FIATModel.from_dict(file_contents)
