"""Implement fiat model class"""

import logging
from hydromt.models.model_api import Model
from hydromt_fiat.reader import Reader
from hydromt_fiat.writer import Writer
from hydromt_fiat.workflows.vulnerability import Vulnerability


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

    def setup_config(self):
        # TODO: check if this is required
        NotImplemented

    def setup_exposure_vector(self, region, **kwargs):
        NotImplemented
        # workflows.exposure_vector.Exposure

    def setup_exposure_raster(self):
        NotImplemented

    def setup_vulnerability(
        self,
        vulnerability_source: str,
        vulnerability_identifiers_and_linking: str,
        unit: str,
    ) -> None:
        """Setup the vulnerability curves from various possible inputs.

        Parameters
        ----------
        vulnerability_source : str
            The (relative) path or ID from the data catalog to the source of the vulnerability functions.
        vulnerability_identifiers_and_linking : str
            The (relative) path to the table that links the vulnerability functions and exposure categories.
        unit : str
            The unit of the vulnerability functions.
        """
        vul = Vulnerability(self.data_catalog)
        vul.get_vulnerability_functions_from_one_file(
            vulnerability_source, vulnerability_identifiers_and_linking, unit
        )

    def setup_hazard(self):
        NotImplemented

    def setup_social_vulnerability_index(self):
        NotImplemented

    def read(self):
        reader = Reader()
        reader.read_config()
        reader.read_staticmaps()
        reader.read_staticgeoms()

    def write(self):
        writer = Writer()
        writer.write_staticmaps()
        writer.write_staticgeoms()
        writer.write_config()
