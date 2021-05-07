"""Implement fiat model class"""
# FIXME implement model class following model API

from typing import List, Set, Dict, Tuple, Optional
import glob
from os.path import join, basename, dirname, abspath, isfile
from pathlib import Path
import logging
from rasterio.warp import transform_bounds
import pyproj
import geopandas as gpd
from shapely.geometry import box
import xarray as xr
import numpy as np
from itertools import cycle
from openpyxl import load_workbook
from ast import literal_eval

import hydromt
from hydromt.models.model_api import Model
from hydromt import gis_utils

from . import workflows, DATADIR

logger = logging.getLogger(__name__)


class FiatModel(Model):
    """General and basic API for the FIAT model in HydroMT"""

    # FIXME
    _NAME = "fiat"
    _CONF = "fiat_configuration.xlsx"
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
        logger=logger,
        deltares_data=False,
    ):
        super().__init__(
            root=root,
            mode=mode,
            config_fn=config_fn,
            data_libs=data_libs,
            deltares_data=deltares_data,
            logger=logger,
        )

    ## components

    def setup_basemaps(self, region, **kwargs):
        """Define model region.

        Adds model layers:

        * **region** geom: model region

        Parameters
        ----------
        region : dict
            Dictionary describing region of interest, e.g. {'bbox': [xmin, ymin, xmax, ymax]}
            See :py:meth:`~hydromt.workflows.parse_region()` for all options
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
                f"Unknown region kind {kind} for FIAT, "
                "expected one of ['file', 'bbox', 'geom']"
            )
        # set model region geometry
        # for the region geometry there is a shortcut to access it with self.region
        self.set_staticgeoms(geom, "region")

    def setup_hazard(
        self,
        map_fn,
        return_period=None,
        variable=None,
        unit="m",
        **kwargs,
    ):
        """Add a hazard map to the FIAT model schematization.

        The method

        Adds model layers:

        * **hazard** map(s): A hazard map with the nomenclature <hazard_type>_rp<return_period>

        Parameters
        ----------
        map_fn: (list of) str, Path
            Path to hazard raster file.
        return_period: int, float, optional
            Return period in years, required for risk calculation. The default is None.
        variable: str
            Name of variable in dataset, required when reading netcdf data.
        unit: str
            Hazard unit, by default 'm'
        """
        # check options
        rp_lst, var_lst = [], []
        fn_lst = [map_fn] if isinstance(map_fn, (str, Path)) else map_fn
        if not (isinstance(fn_lst, list) and isinstance(fn_lst[0], (str, Path))):
            raise TypeError(f"'map_fn' should be a of str or Path type")
        if variable is not None:
            var_lst = [variable] if isinstance(variable, str) else variable
            if not isinstance(var_lst, list):
                raise TypeError(f"'variable' should be a str, got {type(variable)}")
            if len(fn_lst) == 1:
                kwargs.update(variables=var_lst)
        if return_period is not None:
            rp_lst = (
                [return_period]
                if isinstance(return_period, (int, float))
                else return_period
            )
            if not isinstance(rp_lst, list):
                raise TypeError(
                    f"'return_period' should be a float or int, got {type(return_period)}"
                )
            if not (len(rp_lst) == len(fn_lst) or len(rp_lst) == len(var_lst)):
                raise IndexError(
                    "The length of 'return_period' should match with 'map_fn' or 'variable'."
                )

        # Get clipped hazard map dataset. Multiple files are read and merged.
        # NOTE always return a Dataset, also for single layer
        rp = None
        for i, fn in enumerate(fn_lst):
            if str(fn).endswith(".nc"):
                if variable is None:
                    raise ValueError("'variable' required when reading netcdf data.")
                kwargs.update(driver="netcdf")
            if len(fn_lst) == len(var_lst):
                kwargs.update(variables=[var_lst[i]])
            if len(fn_lst) == len(rp_lst):
                rp = rp_lst[i]
            ds = self.data_catalog.get_rasterdataset(
                fn, geom=self.region, single_var_as_array=False, **kwargs
            )
            if self.staticmaps and not self.staticmaps.raster.identical_grid(ds):
                raise ValueError("The hazard maps should have identical grids.")
            # rename and add to staticmaps
            hazard_type = self.get_config("hazard_type", fallback="flooding")
            for j, name in enumerate(ds.data_vars):
                da = ds[name]
                # get return period per data variable
                if len(rp_lst) == len(var_lst) == len(ds.data_vars):
                    rp = rp_lst[j]
                elif len(ds.data_vars) > 1:  # try to infer from dataset names
                    try:
                        # get numeric part (including ".") after "rp" (if in name)
                        fstrip = lambda x: x in "0123456789."
                        rps = "".join(filter(fstrip, name.lower().split("rp")[-1]))
                        rp = literal_eval(rps)
                        assert isinstance(rp, (int, float))
                    except (ValueError, AssertionError):
                        raise ValueError(
                            f"Could not infer return periods for hazard map: {name}"
                        )
                rp_str = f"_rp{rp}" if rp is not None else ""
                out_name = f"{hazard_type}{rp_str}"
                hazard_fn = join(self.root, "hazard", f"{out_name}.tif")
                self.set_staticmaps(da, out_name)
                # update config with filepath
                if rp is not None:
                    post = f" (rp {rp})"
                    # write to hazard dict {rp: filename}
                    self.set_config("hazard", rp, hazard_fn)
                else:
                    post = ""
                    self.set_config("hazard", hazard_fn)
                self.logger.debug(f"Added {hazard_type} hazard layer: {out_name}{post}")

    def setup_exposure_buildings(self, pop_fn, bld_fn, unit="persons", **kwargs):
        # NOTE: why is the catagory refered to as buildings while the unit is persons??
        if self.root is None:
            raise ValueError("No model root defined, set using set_root() method.")
        # NOTE: not tested! > only te describe general pipeline
        # get clip of population count map as DataArray
        da_pop = self.data_catalog.get_rasterdataset(
            pop_fn, variable=["pop"], geom=self.region
        )
        # get clip of building footprint map as DataArray
        da_bld = self.data_catalog.get_rasterdataset(
            bld_fn, variable=["bld"], geom=self.region
        )
        # downscale population map based on building footprints
        # TODO fix downscale_population method
        da_pop_reproj = workflows.downscale_population(
            da_pop, da_bld, ds_like=self.staticmaps
        )
        da_pop_reproj.attrs.update(unit=unit)
        # add layer to staticmaps
        category = "buildings"
        self.set_staticmaps(da_pop_reproj, name=category)
        # get max damage & damage function # TODO
        max_damage, function = self._get_damage_function(**kwargs)
        # add layer to config
        exp_layer = {
            "use": 1,
            "category": category,
            "max_damage": max_damage,
            "function": function,
            "map": 1,
            "weight": 1,
            "raster": join(self.get_config("exposure", fallback=""), f"{category}.tif"),
            "unit": unit,
        }
        lyrs = [int(key.split("_")[1]) for key in self.config if key.startswith("exp_")]
        ilyr = 1 if len(lyrs) == 0 else max(lyrs) + 1
        self.set_config(f"exp_{ilyr}", exp_layer)

    def setup_exposure_raster(self, exposure_fn, category, unit, **kwargs):
        # TODO general method to set exposure layer
        pass

    def setup_exposure_vector(self, exposure_fn, category, **kwargs):
        pass

    def _get_damage_function(self, country, **kwargs):
        # TODO: read damage function and global configuration files
        # TODO: can we lookup country from shapefile?
        pass

    ### overwrite model_api methods for root and config

    def set_root(self, root, mode="w"):
        """Initialized the model root.
        In read mode it checks if the root exists.
        In write mode in creates the required model folder structure

        Parameters
        ----------
        root : str, optional
            path to model root
        mode : {"r", "r+", "w"}, optional
            read/write-only mode for model files
        """
        # do super method & update absolute paths in config
        super().set_root(root=root, mode=mode)
        if self._write and root is not None:
            root = abspath(root)
            self.set_config("vulnerability", join(root, "vulnerability"))
            self.set_config("exposure", join(root, "exposure"))
            self.set_config("output", join(root, "output"))
            hazard_maps = self.get_config("hazard")
            if isinstance(hazard_maps, dict):
                hazard_maps = {
                    k: join(root, "hazard", basename(v)) for k, v in hazard_maps.items()
                }
                self.set_config("hazard", hazard_maps)
            elif isinstance(hazard_maps, str):
                self.set_config("hazard", join(root, "hazard", basename(hazard_maps)))

    def _configread(self, fn):
        """Parse fiat_configuration.xlsx and risk.csv to dict"""
        wb = load_workbook(filename=fn)
        ws = wb["Input"]
        config = dict()
        # hazard
        hazard_fn = ws["B4"].value
        if hazard_fn == "risk.csv":
            hazard_maps = {}
            with open(join(dirname(fn), "risk.csv"), "r") as f:
                lines = f.readlines()
                for line in lines[1:]:  # skip first line with rpmin, rpmax
                    map_fn, rp = line.strip("\n").split(",", maxsplit=2)
                    # strip white spaces and parse rp to int or float with literal_eval
                    hazard_maps.update({literal_eval(rp.strip()): map_fn.strip()})
            config.update({"hazard": hazard_maps})
        elif isinstance(hazard_fn, str):
            config.update({"hazard": hazard_fn})
        # global
        main_conf = {
            "results": ws["B2"].value,
            "hazard_type": ws["B5"].value,  # added to config
            "currency": ws["I1"].value,
            "language": ws["I2"].value,
            "vulnerability": ws["J3"].value,
            "exposure": ws["J4"].value,
            "output": ws["J5"].value,
        }
        # drop empty keys (value is None)
        main_conf = {k: v for k, v in main_conf.items() if v is not None}
        config.update(main_conf)
        for row in range(7, 99):
            if ws[f"A{row}"].value is None:
                break
            exp_layer = {
                "use": ws[f"A{row}"].value,
                "category": ws[f"B{row}"].value,
                "max_damage": ws[f"C{row}"].value,
                "function": ws[f"F{row}"].value,
                "map": ws[f"H{row}"].value,
                "weight": ws[f"I{row}"].value,
                "raster": ws[f"J{row}"].value,
                "unit": ws[f"K{row}"].value,
                "landuse": ws[f"L{row}"].value,
            }
            # drop empty keys (value is None)
            exp_layer = {k: v for k, v in exp_layer.items() if v is not None}
            config.update({f"exp_{row-6}": exp_layer})
        wb.close()
        return config

    def _configwrite(self, fn):
        """Write config to fiat_configuration.xlsx and risk.csv"""
        # load template
        fn_temp = join(self._DATADIR, self._NAME, self._CONF)
        wb = load_workbook(filename=fn_temp)
        ws = wb["Input"]
        # risk.csv
        hazard_maps = self.get_config("hazard")
        if isinstance(hazard_maps, dict):  # multiple hazard layers for different rps
            rpmin, rpmax = min(hazard_maps.keys()), max(hazard_maps.keys())
            with open(join(dirname(fn), "risk.csv"), "w") as f:
                f.write(f"{rpmin}, {rpmax}\n")
                for rp in sorted(hazard_maps.keys()):
                    map_fn = abspath(hazard_maps[rp])
                    f.write(f"{map_fn:s}, {rp}\n")
            ws["B4"] = "risk.csv"
        elif isinstance(hazard_maps, str):  # single hazard layer
            ws["B4"] = abspath(hazard_maps)
        # global
        conf_glob = {
            "B2": "results",
            "B5": "hazard_type",
            "I1": "currency",
            "I2": "language",
            "J3": "vulnerability",
            "J4": "exposure",
            "J5": "output",
        }
        for loc, key in conf_glob.items():
            value = self.get_config(key)
            if value is not None:
                ws[loc] = str(value)
        # layers
        for row in range(7, 99):
            exp_layer = self.get_config(f"exp_{row-6}", fallback={})
            if not exp_layer:
                break
            # write with fallback options
            ws[f"A{row}"] = int(exp_layer.get("use", 0))
            ws[f"B{row}"] = str(exp_layer.get("category", ""))
            ws[f"C{row}"] = float(exp_layer.get("max_damage", 0))
            ws[f"F{row}"] = str(exp_layer.get("function", ""))
            ws[f"H{row}"] = int(exp_layer.get("map", 1))
            ws[f"I{row}"] = int(exp_layer.get("weight", 1))
            ws[f"J{row}"] = str(exp_layer.get("raster", ""))
            ws[f"K{row}"] = str(exp_layer.get("unit", ""))
            ws[f"L{row}"] = str(exp_layer.get("landuse", ""))
        # writ to file
        wb.save(fn)
        wb.close()

    ## I/O
    def read(self):
        """Method to read the complete model schematization and configuration from file."""
        self.logger.info(f"Reading model data from {self.root}")
        self.read_config()
        self.read_staticmaps()
        self.read_staticgeoms()

    def write(self):
        """Method to write the complete model schematization and configuration to file."""
        self.logger.info(f"Writing model data to {self.root}")
        # if in r, r+ mode, only write updated components
        if not self._write:
            self.logger.warning("Cannot write in read-only mode")
            return
        if self.config:  # try to read default if not yet set
            self.write_config()
        if self._staticmaps:
            self.write_staticmaps()
        if self._staticgeoms:
            self.write_staticgeoms()
        if self._forcing:
            self.write_forcing()

    def read_staticmaps(self):
        """Read staticmaps at <root/?/> and parse to xarray Dataset"""
        # to read gdal raster files use: hydromt.open_mfraster()
        # to read netcdf use: xarray.open_dataset()
        if not self._write:
            # start fresh in read-only mode
            self._staticmaps = xr.Dataset()
        # read hazard maps
        hazard_maps = self.get_config("hazard")
        fn_lst = []
        if isinstance(hazard_maps, dict):
            fn_lst = list(hazard_maps.values())
        elif isinstance(hazard_maps, str):
            fn_lst = [hazard_maps]
        for fn in fn_lst:
            name = basename(fn).rsplit(".", maxsplit=2)[0]
            if not isfile(fn):
                logger.warning(f"Could not find hazard map at {fn}")
            else:
                self.set_staticmaps(hydromt.open_raster(fn), name=name)
        # read exposure maps
        exp_root = self.get_config("exposure")
        if exp_root is not None:
            fns = glob.glob(join(exp_root, "*.tif"))
            if len(fns) == 0:
                logger.warning(f"Could not find any expsure maps in {exp_root}")
            else:
                self.set_staticmaps(hydromt.open_mfraster(fns))

    def write_staticmaps(self, compress="lzw"):
        """Write staticmaps at <root/?/> in model ready format"""
        # to write to gdal raster files use: self.staticmaps.raster.to_mapstack()
        # to write to netcdf use: self.staticmaps.to_netcdf()
        if not self._write:
            raise IOError("Model opened in read-only mode")
        hazard_type = self.get_config("hazard_type", fallback="flooding")
        hazard_maps = [n for n in self.staticmaps.data_vars if hazard_type in n]
        if len(hazard_maps) > 0:
            self.staticmaps[hazard_maps].raster.to_mapstack(
                join(self.root, "hazard"), compress=compress
            )
        exposure_maps = [n for n in self.staticmaps.data_vars if hazard_type not in n]
        if len(exposure_maps) > 0:
            exp_root = self.get_config("exposure")
            self.staticmaps[hazard_maps].raster.to_mapstack(exp_root, compress=compress)
        # TODO write exposure maps

    def read_staticgeoms(self):
        """Read staticgeoms at <root/?/> and parse to dict of geopandas"""
        if not self._write:
            # start fresh in read-only mode
            self._staticgeoms = dict()
        return self._staticgeoms

    def write_staticgeoms(self):
        """Write staticmaps at <root/?/> in model ready format"""
        if not self._write:
            raise IOError("Model opened in read-only mode")
        if self._staticgeoms:
            for name, gdf in self._staticgeoms.items():
                gdf.to_file(join(self.root, f"{name}.geojson"), driver="GeoJSON")

    def read_forcing(self):
        """Read forcing at <root/?/> and parse to dict of xr.DataArray"""
        return self._forcing
        # raise NotImplementedError()

    def write_forcing(self):
        """write forcing at <root/?/> in model ready format"""
        pass
        # raise NotImplementedError()

    def read_states(self):
        """Read states at <root/?/> and parse to dict of xr.DataArray"""
        return self._states
        # raise NotImplementedError()

    def write_states(self):
        """write states at <root/?/> in model ready format"""
        pass
        # raise NotImplementedError()

    def read_results(self):
        """Read results at <root/?/> and parse to dict of xr.DataArray"""
        return self._results
        # raise NotImplementedError()

    def write_results(self):
        """write results at <root/?/> in model ready format"""
        pass
        # raise NotImplementedError()
