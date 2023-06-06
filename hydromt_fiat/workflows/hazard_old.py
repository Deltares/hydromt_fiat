from hydromt_fiat.validation import * 
from pathlib import Path
import geopandas as gpd
from ast import literal_eval
import os
import xarray as xr


class Hazard:
    def __init__(self):
        self.crs = ""
        self.map_fn_lst = []
        self.map_type_lst = []

