"""Implement fiat model class"""

from hydromt.models.model_api import Model
from hydromt_fiat.reader import Reader
from hydromt_fiat.writer import Writer
from hydromt_fiat.workflows.hazard import Hazard
import logging
from pathlib import Path
from hydromt import DataCatalog


from . import DATADIR

__all__ = ["FiatModel"]

_logger = logging.getLogger(__name__)


class FiatModel(Model):
    """General and basic API for the FIAT model in hydroMT."""

    _NAME    = "fiat"
    _CONF    = "fiat_configuration.ini"
    _GEOMS   = {}  # FIXME Mapping from hydromt names to model specific names
    _MAPS    = {}  # FIXME Mapping from hydromt names to model specific names
    _FOLDERS = ["hazard", "exposure", "vulnerability", "output"]
    _DATADIR = DATADIR

    def __init__(
        self,
        root          =None,
        mode          ="w",
        config_fn     =None,
        data_libs     =None,
        logger        =_logger,
        deltares_data =False,
        artifact_data =False,
    ):
        super().__init__(
            root          =root,
            mode          =mode,
            config_fn     =config_fn,
            data_libs     =data_libs,
            logger        =logger,
            deltares_data =deltares_data,
            artifact_data =artifact_data,
        )

    def setup_config(self):
        # TODO: check if this is required
        NotImplemented

    def setup_exposure_vector(self, region, **kwargs):
        NotImplemented
        # workflows.exposure_vector.Exposure

    def setup_exposure_raster(self):
        NotImplemented

    def setup_vulnerability(self):
        NotImplemented

    def setup_hazard(self): 	
        			
        map_fn      = self.get_config('setup_hazard', 'map_fn')			
        map_type    = self.get_config('setup_hazard', 'map_type')				
        rp          = self.get_config('setup_hazard', 'rp')
        crs         = self.get_config('setup_hazard', 'crs')
        nodata      = self.get_config('setup_hazard', 'nodata')
        var         = self.get_config('setup_hazard', 'var')		
        chunks      = self.get_config('setup_hazard', 'chunks')
        risk_output = self.get_config('setup_config','risk_output', fallback=True)
        hazard_type = self.get_config('setup_config','hazard_type', fallback="flooding")

        Hazard().setup_hazard(self,hazard_type=hazard_type,risk_output=risk_output, map_fn=map_fn,map_type=map_type,rp=rp,crs=crs, nodata=nodata,var=var,chunks=chunks)
 
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
