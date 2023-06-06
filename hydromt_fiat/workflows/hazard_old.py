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

    def get_lists(
        self,
        map_fn,
        map_type,
        chunks,
        rp,
        crs,
        nodata,
        var,
            
    ):  
        dict_lists = dict()
        
        def validate_param(dictionary, param, name, types):
            param_lst = [param] if isinstance(param, types) else param
            check_param_type(param_lst, name=name, types=types)
            dictionary[name+'_lst'] = param_lst
            return 

        validate_param(dict_lists, map_fn, name="map_fn", types=(str, Path))
        validate_param(dict_lists, map_type, name="map_type", types=str)
        if chunks != "auto":
            validate_param(dict_lists, chunks, name="chunks", types=(int, dict))
        if rp is not None:
            validate_param(dict_lists, rp, name="rp", types=(float, int))
        if crs is not None:
            validate_param(dict_lists, crs, name="crs", types=(int, str))
        if nodata is not None:
            validate_param(dict_lists, nodata, name="nodata", types=(float, int))
        if var is not None:
            validate_param(dict_lists, var, name="var", types=str)

        return dict_lists
    
    def check_parameters(
        self,
        dict_lists,
        model,
        chunks,
        rp,
        crs,
        nodata,
        var,
    ):
        
        def error_message(variable_list):
            raise IndexError(f"The number of '{variable_list}' parameters should match with the number of 'map_fn' parameters.")
            # raise TypeError(f"The number of '{variable_list}' parameters should match with the number of 'map_fn' parameters.")

        # Checks the hazard input parameter types.

        # Checks map path list
        map_fn_lst   = dict_lists['map_fn_lst']

        # Checks map path list
        if not len(dict_lists['map_type_lst']) == 1 and not len(dict_lists['map_type_lst']) == len(map_fn_lst):
            error_message("map_type")
        
        # Checks the chunk list. The list must be equal to the number of maps.
        if chunks != "auto":
            if not len(dict_lists['chunks_lst']) == 1 and not len(dict_lists['chunks_lst']) == len(map_fn_lst):
                error_message("chunks")
            
        # Checks the return period list. The list must be equal to the number of maps.
        if rp is not None:
            if not len(dict_lists['rp_lst']) == len(map_fn_lst):
                error_message("rp")
            
        # Checks the projection list
        if crs is not None:
            if not len(dict_lists['crs_lst']) == 1 and not len(dict_lists['crs_lst']) == len(map_fn_lst):
                error_message("crs")
            
        # Checks the no data list
        if nodata is not None:
            if not len(dict_lists['nodata_lst']) == 1 and not len(dict_lists['nodata_lst']) == len(map_fn_lst):
                error_message("nodata")
            
        # Checks the var list
        if var is not None:
            if not len(dict_lists['var_lst']) == 1 and not len(dict_lists['var_lst']) == len(map_fn_lst):
                error_message('var')

        # Check if the hazard input files exist.
        check_file_exist(model, param_lst=map_fn_lst, name="map_fn")

    def process_maps(
        self,
        dict_lists,
        model,
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
        map_fn_lst     = dict_lists['map_fn_lst']
        map_type_lst   = dict_lists['map_type_lst']

        list_names   = []
        list_rp      = []

        for idx, da_map_fn in enumerate(map_fn_lst):

            # Check if it is a path or a name from the catalog
            if os.path.exists(da_map_fn):
                da_map_fn = Path(da_map_fn)
                da_name   = da_map_fn.stem
                da_suffix = da_map_fn.suffix
                list_names.append(da_name)
            else:
                da_name = da_map_fn
                list_names.append(da_name)

            da_type = get_param(
                    map_type_lst, 
                    map_fn_lst, 
                    "hazard", 
                    da_name, 
                    idx, 
                    "map type"
            )

            # Get the local hazard map.
            kwargs.update(chunks=chunks if chunks == "auto" else dict_lists['chunks_lst'][idx])

            if "da_suffix" in locals() and da_suffix == ".nc":
                if var is None:
                    raise ValueError(
                        "The 'var' parameter is required when reading NetCDF data."
                    )
                da_var = get_param(
                        dict_lists['var_lst'],
                        map_fn_lst,
                        "hazard",
                        da_name,
                        idx,
                        "NetCDF variable",
                )
                kwargs.update(variables=da_var)

            # reading from path
            if da_map_fn.stem:
                if da_map_fn.stem == "sfincs_map":
                    ds_map = xr.open_dataset(da_map_fn)
                    da     = ds_map[kwargs["variables"]].squeeze(dim="timemax").drop_vars("timemax")
                    da.raster.set_crs(ds_map.crs.epsg_code)  
                    da.raster.set_nodata(nodata=ds_map.encoding.get("_FillValue"))
                    da.reset_coords(['spatial_ref'], drop=False)
                    da.encoding["_FillValue"] = None

                else:
                    if not region.empty:
                        da = model.data_catalog.get_rasterdataset(
                            da_map_fn, geom=region, **kwargs
                        )
                    else:
                        da = model.data_catalog.get_rasterdataset(da_map_fn, **kwargs)
            # reading from the datacatalog
            else:
                if not region.empty:
                    da = model.data_catalog.get_rasterdataset(
                        name_catalog, variables=da_name, geom=region
                    )
                else:
                    da = model.data_catalog.get_rasterdataset(
                        name_catalog, variables=da_name
                    )

            # Set the coordinate reference system.
            if crs is not None:
                da_crs = get_param(
                        dict_lists['crs_lst'],
                        map_fn_lst,
                        "hazard",
                        da_name,
                        idx,
                        "coordinate reference system",
                )
                da_crs_str = da_crs if "EPSG" in da_crs else f"EPSG:{da_crs}"
                da.raster.set_crs(da_crs_str)
            elif crs is None and not da.raster.crs:
                raise ValueError(
                    "The hazard map has no coordinate reference system assigned."
                )

            # Set nodata and mask the nodata value.
            if nodata is not None:
                da_nodata = get_param(
                    dict_lists['nodata_lst'], 
                    map_fn_lst, 
                    "hazard", 
                    da_name, 
                    idx, 
                    "nodata"
                )
                da.raster.set_nodata(nodata=da_nodata)
            elif nodata is None and da.raster.nodata is None:
                raise ValueError("The hazard map has no nodata value assigned.")
            

           # Correct (if necessary) the grid orientation from the lower to the upper left corner.
           # This check could not be implemented into the sfincs_map outputs. They require to be transformed to geotiff first
            if da_name != "sfincs_map":            
                if da.raster.res[1] > 0:
                    da = da.reindex(
                        {da.raster.y_dim: list(reversed(da.raster.ycoords))}
                        )
                
            # Check if the obtained hazard map is identical.
            if model.staticmaps and not model.staticmaps.raster.identical_grid(da):
                raise ValueError("The hazard maps should have identical grids.")

            # Get the return period input parameter.
            if 'rp_lst' in dict_lists:
                da_rp = get_param(
                        dict_lists['rp_lst'],
                        map_fn_lst,
                        "hazard",
                        da_name,
                        idx,
                        "return period",
                    )
            else:
                 da_rp =None

            if risk_output:
                da = da.expand_dims({'rp': [da_rp]}, axis=0)

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
            check_uniqueness(
                model,
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
                    "var": None if not 'var_lst' in dict_lists else dict_lists['var_lst'][idx],
                    "chunks": "auto" if chunks == "auto" else dict_lists['chunks_lst'][idx],
                },
                file_type="hazard",
                filename=da_name,
            )

            model.set_config(
                "hazard",
                da_type,
                da_name,
                {
                    "usage": "True",
                    "map_fn": da_map_fn,
                    "map_type": da_type,
                    "rp": da_rp,
                    "crs": da.raster.crs,
                    "nodata": da.raster.nodata,
                    # "var": None if "var_lst" not in locals() else self.var_lst[idx],
                    "var": None if not 'var_lst' in dict_lists else dict_lists['var_lst'][idx],
                    "chunks": "auto" if chunks == "auto" else dict_lists['chunks_lst'][idx],
                },
            )

            model.set_maps(da, da_name)
            post = f"(rp {da_rp})" if risk_output else ""
            model.logger.info(f"Added {hazard_type} hazard map: {da_name} {post}")

        if risk_output:
            maps = model.maps
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
                            'name':list_names,
                            "Analysis": "Risk"}  

            model.hazard = new_da
            model.set_maps(model.hazard, 'HydroMT_Fiat_hazard')

            list_maps = list(model.maps.keys())

            if risk_output:
                for item in list_maps[:-1]:
                    model.maps.pop(item)

