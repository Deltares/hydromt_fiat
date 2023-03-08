"""Implement fiat model class"""

from hydromt.models.model_api import Model
from pathlib import Path
from shapely.geometry import box
from shutil import copy
import geopandas as gpd
import hydromt
import logging


from . import DATADIR

__all__ = ["FiatModel"]

_logger = logging.getLogger(__name__)


class FiatModel(Model):
    """General and basic API for the FIAT model in hydroMT."""

    _NAME = "fiat"
    _CONF = "fiat_configuration.ini"
    _GEOMS = {}  # FIXME Mapping from hydromt names to model specific names
    _MAPS = {}  # FIXME Mapping from hydromt names to model specific names
    _FOLDERS = ["hazard", "exposure", "vulnerability", "output"]
    _DATADIR = DATADIR

    def __init__(
        self,
        root=None,
        mode="w",
        config_fn=None,
        data_libs=None,
        logger=_logger,
        deltares_data=False,
        artifact_data=False,
    ):
        super().__init__(
            root=root,
            mode=mode,
            config_fn=config_fn,
            data_libs=data_libs,
            deltares_data=deltares_data,
            artifact_data=artifact_data,
            logger=logger,
        )

    def setup_basemaps(
        self,
        region,
        **kwargs,
    ):
        """Define the model domain that is used to clip the raster layers.

        Adds model layer:

        * **region** geom: A geometry with the nomenclature 'region'.

        Parameters
        ----------
        region: dict
            Dictionary describing region of interest, e.g. {'bbox': [xmin, ymin, xmax, ymax]}. See :py:meth:`~hydromt.workflows.parse_region()` for all options.
        """

        kind, region = hydromt.workflows.parse_region(region, logger=self.logger)
        if kind == "bbox":
            geom = gpd.GeoDataFrame(geometry=[box(*region["bbox"])], crs=4326)
        elif kind == "grid":
            geom = region["grid"].raster.box
        elif kind == "geom":
            geom = region["geom"]
        else:
            raise ValueError(
                f"Unknown region kind {kind} for FIAT, expected one of ['bbox', 'grid', 'geom']."
            )

        # Set the model region geometry (to be accessed through the shortcut self.region).
        self.set_geoms(geom, "region")

    def set_root(self, root=None, mode="w"):
        """Initialized the model root.
        In read mode it checks if the root exists.
        In write mode in creates the required model folder structure.

        Parameters
        ----------
        root: str, optional
            Path to model root.
        mode: {"r", "r+", "w"}, optional
            Read/write-only mode for model files.
        """

        # Do super method and update absolute paths in config.
        if root is None:
            root = Path(self._config_fn).parent
        super().set_root(root=root, mode=mode)
        if self._write and root is not None:
            self._root = Path(root)

            # Set the general information.
            self.set_config("hazard_dp", self.root.joinpath("hazard"))
            self.set_config("exposure_dp", self.root.joinpath("exposure"))
            self.set_config("vulnerability_dp", self.root.joinpath("vulnerability"))
            self.set_config("output_dp", self.root.joinpath("output"))

            # Set the hazard information.
            if self.get_config("hazard"):
                for hazard_type, hazard_scenario in self.get_config("hazard").items():
                    for hazard_fn in hazard_scenario:
                        hazard_scenario[hazard_fn]["map_fn"] = self.get_config(
                            "hazard_dp"
                        ).joinpath(hazard_scenario[hazard_fn]["map_fn"].name)
                        self.set_config(
                            "hazard",
                            hazard_type,
                            hazard_fn,
                            hazard_scenario[hazard_fn],
                        )
            if self.get_config("exposure"):
                for exposure_fn in self.get_config("exposure"):
                    self.set_config(
                        "exposure",
                        exposure_fn,
                        "map_fn",
                        self.get_config("exposure_dp").joinpath(
                            self.get_config("exposure", exposure_fn, "map_fn").name,
                        ),
                    )
                    for sf_path in self.get_config(
                        "exposure",
                        exposure_fn,
                        "function_fn",
                    ).values():
                        if (
                            not self.get_config("vulnerability_dp")
                            .joinpath(
                                sf_path.name,
                            )
                            .is_file()
                        ):
                            copy(
                                sf_path,
                                self.get_config("vulnerability_dp").joinpath(
                                    sf_path.name,
                                ),
                            )
                    self.set_config(
                        "exposure",
                        exposure_fn,
                        "function_fn",
                        {
                            i: self.get_config("vulnerability_dp").joinpath(j.name)
                            for i, j in self.get_config(
                                "exposure",
                                exposure_fn,
                                "function_fn",
                            ).items()
                        },
                    )
