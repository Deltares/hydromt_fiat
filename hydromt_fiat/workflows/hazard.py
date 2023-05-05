from hydromt_fiat.validation import Validation
from pathlib import Path
import geopandas as gpd
from ast import literal_eval
import os
import xarray as xr


class Hazard:
    def __init__(self):
        self.crs = ""
        self.check = Validation()
    
    def checkInputs(
        self,
        model_fiat,
        map_fn,
        map_type,
        chunks,
        rp,
        crs,
        nodata,
        var,
    ):
        
        # Checks the hazard input parameter types.
        # Checks map path list
        self.map_fn_lst   = [map_fn]  if isinstance(map_fn, (str, Path)) else map_fn
        self.check.check_param_type(self.map_fn_lst, name="map_fn", types=(str, Path))
        # Checks map path list
        self.map_type_lst = [map_type] if isinstance(map_type, (str, Path)) else map_type
        self.check.check_param_type(self.map_type_lst, name="map_type", types=str)
        if not len(self.map_type_lst) == 1 and not len(self.map_type_lst) == len(self.map_fn_lst):
            raise IndexError(
                "The number of 'map_type' parameters should match with the number of "
                "'map_fn' parameters."
            )
        # Checks the chunk list. The list must be equal to the number of maps.
        if chunks != "auto":
            self.chunks_lst = [chunks] if isinstance(chunks, (int, dict)) else chunks
            self.check.check_param_type(self.chunks_lst, name="chunks", types=(int, dict))
            if not len(self.chunks_lst) == 1 and not len(self.chunks_lst) == len(self.map_fn_lst):
                raise IndexError(
                    "The number of 'chunks' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        # Checks the return period list. The list must be equal to the number of maps.   
        if rp is not None:
            rp_lst_check = True 
            self.rp_lst = [rp] if isinstance(rp, (int, float)) else rp
            self.check.check_param_type(self.rp_lst, name="rp", types=(float, int))
            if not len(self.rp_lst) == len(self.map_fn_lst):
                raise IndexError(
                    "The number of 'rp' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        # Checks the projection list 
        if crs is not None:
            self.crs_lst = [str(crs)] if isinstance(crs, (int, str)) else crs
            self.check.check_param_type(self.crs_lst, name="crs", types=(int, str))
            if not len(self.crs_lst) == 1 and not len(self.crs_lst) == len(self.map_fn_lst):
                raise IndexError(
                    "The number of 'crs' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        # Checks the no data list  
        if nodata is not None:
            self.nodata_lst = [nodata] if isinstance(nodata, (float, int)) else nodata
            self.check.check_param_type(self.nodata_lst, name="nodata", types=(float, int))
            if not len(self.nodata_lst) == 1 and not len(self.nodata_lst) == len(self.map_fn_lst):
                raise IndexError(
                    "The number of 'nodata' parameters should match with the number of "
                    "'map_fn' parameters."
                )
         # Checks the var list    
        if var is not None:
            self.var_lst = [var] if isinstance(var, str) else var
            self.check.check_param_type(self.var_lst, name="var", types=str)
            if not len(self.var_lst) == 1 and not len(self.var_lst) == len(self.map_fn_lst):
                raise IndexError(
                    "The number of 'var' parameters should match with the number of "
                    "'map_fn' parameters."
                )

        # Check if the hazard input files exist.
        self.check.check_file_exist(model_fiat.root, param_lst=self.map_fn_lst, name="map_fn")


    def readMaps(
        self,
        model_fiat,
        name_catalog,
        hazard_type,
        risk_output,
        crs,
        nodata,
        var,
        chunks,
        region=gpd.GeoDataFrame(),
        **kwargs,
    ):
     
        #This list of names should be provided to have the maps in order
        # catalog         = model_fiat.data_catalog.get_rasterdataset(name_catalog)
        # self.map_fn_lst = [i for i in list(catalog.variables) if maps_id in i]
        
        # Read the hazard map(s) and add to config and staticmaps.
        list_rp = []
        list_names = []

        for idx, da_map_fn in enumerate(self.map_fn_lst):
            # Check if it is a path or a name from the catalog 

            if os.path.exists(da_map_fn):
                da_map_fn = Path(da_map_fn)
                da_name = da_map_fn.stem
                da_suffix = da_map_fn.suffix
                list_names.append(da_name)

            else:   
                da_name = da_map_fn
                list_names.append(da_name)
            
            da_type = self.check.get_param(
                self.map_type_lst, 
                self.map_fn_lst, 
                "hazard", 
                da_name, 
                idx, 
                "map type"
            )

            # Get the local hazard map.
            kwargs.update(chunks=chunks if chunks == "auto" else self.chunks_lst[idx])

            if "da_suffix" in locals() and da_suffix == ".nc":
                if var is None:
                    raise ValueError(
                        "The 'var' parameter is required when reading NetCDF data."
                    )
                kwargs.update(
                    variables=self.check.get_param(
                        self.var_lst,
                        self.map_fn_lst,
                        "hazard",
                        da_name,
                        idx,
                        "NetCDF variable",
                    )
                )

            if os.path.exists(da_map_fn):
                if not region.empty:
                    da = model_fiat.data_catalog.get_rasterdataset(
                        da_map_fn, geom=region, **kwargs
                    )
                    var_test ='1'
                else:
                    da = model_fiat.data_catalog.get_rasterdataset(da_map_fn, **kwargs)
                    var_test ='2'
            else:
                if not region.empty:
                    da = model_fiat.data_catalog.get_rasterdataset(
                        name_catalog, variables=da_name, geom=region
                    )
                    var_test ='3'
                else:
                    da = model_fiat.data_catalog.get_rasterdataset(
                        name_catalog, variables=da_name
                    )
                    var_test ='4'

            # Set (if necessary) the coordinate reference system.
            # if crs is not None and not da.raster.crs.is_epsg_code:
            # if crs is not None and not da.raster.crs:
            # Change to be defined by the user
            if crs is not None:
                da_crs = self.check.get_param(
                    self.crs_lst,
                    self.map_fn_lst,
                    "hazard",
                    da_name,
                    idx,
                    "coordinate reference system",
                )
                da_crs_str = da_crs if "EPSG" in da_crs else f"EPSG:{da_crs}"
                da.raster.set_crs(da_crs_str)
            # elif crs is None and not da.raster.crs.is_epsg_code:
            elif crs is None and not da.raster.crs:
                raise ValueError("The hazard map has no coordinate reference system assigned.")

            # Set (if necessary) and mask the nodata value.
            if nodata is not None:
                da_nodata = self.check.get_param(
                    self.nodata_lst, 
                    self.map_fn_lst, 
                    "hazard", 
                    da_name, 
                    idx, 
                    "nodata"
                )
                da.raster.set_nodata(nodata=da_nodata)
            elif nodata is None and da.raster.nodata is None:
                raise ValueError("The hazard map has no nodata value assigned.")
            
            # Correct (if necessary) the grid orientation from the lower to the upper left corner.
            if da.raster.res[1] > 0:
                da = da.reindex(
                    {da.raster.y_dim: list(reversed(da.raster.ycoords))}
                    )
                
            # Check if the obtained hazard map is identical.
            if (
                model_fiat.staticmaps
                and not model_fiat.staticmaps.raster.identical_grid(da)
            ):
                raise ValueError("The hazard maps should have identical grids.")

            # Get the return period input parameter.
            da_rp = (
                self.check.get_param(
                    self.rp_lst, 
                    self.map_fn_lst, 
                    "hazard", 
                    da_name, 
                    idx, 
                    "return period"
                )
                if hasattr(self, "rp_lst ") 
                else None
            )
        
            if risk_output and da_rp is None:
                
                # Get (if possible) the return period from dataset names if the input parameter is None.
                if "rp" in da_name.lower():

                    def fstrip(x):
                        return x in "0123456789."

                    rp_str = "".join(
                        filter(fstrip, da_name.lower().split("rp")[-1])
                    ).lstrip("0")

                    try:
                        assert isinstance(
                            literal_eval(rp_str) if rp_str else None, (int, float)
                        )
                        da_rp = literal_eval(rp_str)
                        list_rp.append(da_rp)

                    except AssertionError:
                        raise ValueError(
                            f"Could not derive the return period for hazard map: {da_name}."
                        )
                else:
                    raise ValueError(
                        "The hazard map must contain a return period in order to conduct a risk calculation."
                    )
                
            # Add the hazard map to config and staticmaps.
            self.check.check_uniqueness(
                model_fiat,
                "hazard",
                da_type,
                da_name,
                {
                    "usage": True,
                    "map_fn": da_map_fn,
                    "map_type": da_type,
                    "rp": da_rp,
                    "crs": da.raster.crs,
                    "nodata": da.raster.nodata,
                    # "var": None if "var_lst" not in locals() else self.var_lst[idx],
                    "var": None if not hasattr(self, "var_lst") else self.var_lst[idx],
                    "chunks": "auto" if chunks == "auto" else self.chunks_lst[idx],
                },
                file_type="hazard",
                filename=da_name,
            )

            model_fiat.set_config(
                "hazard",
                # da_type,
                da_name,
                {
                    "usage": "True",
                    "map_fn": da_map_fn,
                    "map_type": da_type,
                    "rp": da_rp,
                    "crs": da.raster.crs,
                    "nodata": da.raster.nodata,
                    # "var": None if "var_lst" not in locals() else self.var_lst[idx],
                    "var": None if not hasattr(self, "var_lst") else self.var_lst[idx],
                    "chunks": "auto" if chunks == "auto" else self.chunks_lst[idx],
                },
            ) 

            #extra functionalities 
            # da = da.rename(f"map_{da_rp}")
            # da.attrs = {
            #             "usage": "True",
            #             "map_fn": da_map_fn,
            #             "map_type": da_type,
            #             "rp": da_rp,
            #             "crs": da.raster.crs,
            #             "nodata": da.raster.nodata,
            #             # "var": None if "var_lst" not in locals() else self.var_lst[idx],
            #             "var": None if not hasattr(self, "var_lst") else self.var_lst[idx],
            #             "chunks": "auto" if chunks == "auto" else self.chunks_lst[idx],
            #            }
            
            da = da.expand_dims({'rp': [da_rp]}, axis=0)

            model_fiat.set_maps(da, da_name)
            # post = f"(rp {da_rp})" if rp is not None and risk_output else ""
            post = f"(rp {da_rp})" if risk_output else ""
            model_fiat.logger.info(
                f"Added {hazard_type} hazard map: {da_name} {post}"
            )



            # new_da = xr.concat([new_da, da], dim='rp')   

            # import numpy as np
            # new_da = xr.DataArray(np.zeros_like(da), dims=da.dims, coords=da.coords).rename('new_dataframe')

        # # model_fiat.maps.to_netcdf("test_hazard_1/test.nc")

        # #model_fiat.set_maps(catalog, "all")
        maps = model_fiat.maps
        list_keys = list(maps.keys())
        maps_0 = maps[list_keys[0]].rename('risk')
        list_keys.pop(0)

        for idx, x in enumerate(list_keys):
            key_name = list_keys[idx]
            layer = maps[key_name]
            maps_0 = xr.concat([maps_0, layer], dim='rp') 

        new_da = maps_0.to_dataset(name='RISK')
        new_da.attrs = {  "returnperiod": list(list_rp),
                          "type":self.map_type_lst,
                          'name':list_names}
        
        if not risk_output:
            # new_da = maps_0.drop_dims('rp')
            new_da = maps_0.to_dataset(name='EVENT')
            new_da.attrs = {  "returnperiod": list(list_rp),
                            "type":self.map_type_lst,
                            'name':list_names,
                            "Analysis": "Event base"}       

        else:
            new_da = maps_0.to_dataset(name='RISK')
            new_da.attrs = {  "returnperiod": list(list_rp),
                            "type":self.map_type_lst,
                            'name':list_names,
                            "Analysis": "Risk"}  

        model_fiat.hazard = new_da
        model_fiat.set_maps(model_fiat.hazard, 'HydroMT_Fiat_hazard')

        list_maps = list(model_fiat.maps.keys())

        for item in list_maps[:-1]:
            model_fiat.maps.pop(item)

        # ds = xr.Dataset(maps)
        # ds.raster.set_crs(da.raster.crs)

        # # new_da= ds.to_array(dim='rp')

        # # new_da = new_da.to_dataset(name='Full_stack')

        # # new_da.attrs = {  "returnperiod": list_rp,
        # #                   "type":self.map_type_lst,
        # #                   'name':list_names}
        
        # # for var_name, var_data in ds.variables.items():
        # #     new_da = xr.concat([new_da, ds[var_name]], dim='rp')

        # for layer_name in ds:
        #     layer = ds[layer_name]
        #     new_da = xr.concat([new_da, layer], dim='rp')

        # # new_da = new_da.to_dataset()
        
        # # config = model_fiat.config
        # # new_da.to_netcdf("P:/11207949-dhs-phaseii-floodadapt/Model-builder/Delft-FIAT/local_test_database/test_hazard_1/hazard/test_final_v2.nc")
        # #C:\Users\fuentesm\CISNE\HydroMT_sprint_sessions
        return model_fiat.maps 
