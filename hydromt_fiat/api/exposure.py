from hydromt_fiat.interface.database import IDatabase
from hydromt_fiat.loader import ConfigHandler, HydroMTConfig


def save_interest_area(filename, database: IDatabase) -> int:
    
    if (database.save(folder = "exposure", filename: str)): 
        return 1
    return 0
    

def save_location_source(filename: str, database: IDatabase):
    if (database.save(folder = "exposure", filename)): 
        return 1
    return 0                                  


def set_object_extraction(config: ConfigHandler, method = "centroid"):
    config.attrs.setup_exposure_vector.extraction_method = method
    
    
    
    
    
