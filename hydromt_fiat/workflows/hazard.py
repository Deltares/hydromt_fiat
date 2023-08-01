from hydromt_fiat.validation import *
from pathlib import Path
import geopandas as gpd
from ast import literal_eval
import os
import xarray as xr

# from hydromt_sfincs import SfincsModel

# from hydromt_sfincs import SfincsModel
from typing import Union
from typing import Tuple
from hydromt.data_catalog import DataCatalog
import geopandas as gpd


def check_parameters_type(
    map_fn: Union[str, Path, list[str], list[Path]],
    map_type: Union[str, list[str]],
    rp: Union[int, list[int], None] = None,
    crs: Union[int, str, list[int], list[str], None] = None,
    nodata: Union[int, list[int], None] = None,
    var: Union[str, list[str], None] = None,
    chunks: Union[int, str, list[int]] = "auto",
) -> dict:
    """Check data type of parameters and save them as list items.

    Parameters
    ----------
    map_fn : Union[str, Path, list[str], list[Path]]
        The data catalog key or list of keys from where to retrieve the
        hazard maps. This can also be a path or list of paths to take files
        directly from a local database.
    map_type : Union[str, list[str]]
        The data type of each map speficied in map_fn. In case a single
        map type applies for all the elements a single string can be provided.
    rp : Union[int, list[int], None], optional.
        The return period (rp) type of each map speficied in map_fn in case a
        risk output is required. If the rp is not provided and risk
        output is required the workflow will try to retrieve the rp from the
        files's name, by default None.
    crs : Union[int, str, list[int], list[str], None], optional
        The projection (crs) required in EPSG code of each of the maps provided. In
        case a single crs applies for all the elements a single value can be
        provided as code or string (e.g. "EPSG:4326"). If not provided, then the crs
        will be taken from orginal maps metadata, by default None.
    nodata : Union[int, list[int], None], optional
        The no data values in the rasters arrays. In case a single no data applies
        for all the elements a single value can be provided as integer, by default
        None.
    var : Union[str, list[str], None], optional
        The name of the variable to be selected in case a netCDF file is provided
        as input, by default None.
    chunks : Union[int, str, list[int]], optional
        The chuck region per map. In case a single no data applies for all the
        elements a single value can be provided as integer. If "auto"is provided
        the auto setting will be provided by default "auto".

    Returns
    -------
    dict
        Dictionary with the parameters and list of parameters used in setup_hazard.
    """
    params = dict()

    params["map_fn"] = map_fn
    params["map_type"] = map_type
    params["chunks"] = chunks
    params["rp"] = rp
    params["crs"] = crs
    params["nodata"] = nodata
    params["var"] = var

    def validate_type(dictionary, param, name, types):
        params_lst = [param] if isinstance(param, types) else param
        check_param_type(params_lst, name=name, types=types)
        dictionary[name + "_lst"] = params_lst
        return

    validate_type(params, map_fn, name="map_fn", types=(str, Path))
    validate_type(params, map_type, name="map_type", types=str)
    if chunks != "auto":
        validate_type(params, chunks, name="chunks", types=(int, dict))
    if rp is not None:
        validate_type(params, rp, name="rp", types=(float, int))
    if crs is not None:
        validate_type(params, crs, name="crs", types=(int, str))
    if nodata is not None:
        validate_type(params, nodata, name="nodata", types=(float, int))
    if var is not None:
        validate_type(params, var, name="var", types=str)
    return params


def check_parameters_size(
    params: dict,
):
    """Check that list of parameters are of the same size in case multiple maps are
    provided to ensure all the maps have their corresponding metadata to process. In
    case the same metadata applies for all the maps a one item list can be provided.
    This excludes return period 'rp'which requires to be defined explicitly per map
    or set to None to try to retrieve the return period from the map names.

    Parameters
    ----------
    params : dict
        Dictionary with the parameters and list of parameters used in setup_hazard.

    Raises
    ------
    IndexError
        Error will be displayed in case metadata is missing in the loaded maps or is
        less than the number of maps.
    """
    # load dictionary variables
    chunks = params["chunks"]
    rp = params["rp"]
    crs = params["crs"]
    nodata = params["nodata"]
    var = params["var"]

    # for key, value in params.items():
    #     globals()[key] = value

    def error_message(variable_list):
        raise IndexError(
            f"The number of '{variable_list}' parameters should match with the number of 'map_fn' parameters."
        )
        # TODO: check what type of error is better to apply in this case
        # raise TypeError(f"The number of '{variable_list}' parameters should match with the number of 'map_fn' parameters.")

    # Checks the hazard input parameter types.

    # Checks map type list
    if not len(params["map_type_lst"]) == 1 and not len(params["map_type_lst"]) == len(
        params["map_fn_lst"]
    ):
        error_message("map_type")

    # Checks the chunk list. The list must be equal to the number of maps.
    if chunks != "auto":
        if not len(params["chunks_lst"]) == 1 and not len(params["chunks_lst"]) == len(
            params["map_fn_lst"]
        ):
            error_message("chunks")

    # Checks the return period list. The list must be equal to the number of maps.
    if rp is not None:
        if not len(params["rp_lst"]) == len(params["map_fn_lst"]):
            error_message("rp")

    # Checks the projection list
    if crs is not None:
        if not len(params["crs_lst"]) == 1 and not len(params["crs_lst"]) == len(
            params["map_fn_lst"]
        ):
            error_message("crs")

    # Checks the no data list
    if nodata is not None:
        if not len(params["nodata_lst"]) == 1 and not len(params["nodata_lst"]) == len(
            params["map_fn_lst"]
        ):
            error_message("nodata")

    # Checks the var list
    if var is not None:
        if not len(params["var_lst"]) == 1 and not len(params["var_lst"]) == len(
            params["map_fn_lst"]
        ):
            error_message("var")


def check_files(
    params: dict,
    root: str,
):
    """Check if the provided files paths exists. I will raise an error in case the
    flood maps does not exist

    Parameters
    ----------
    params : dict
        Dictionary with the parameters and list of parameters used in setup_hazard.
    root : str
        The root directory of the model.
    """
    # load dictionary variables
    map_fn_lst = params["map_fn_lst"]

    # Check if the hazard input files exist.
    check_file_exist(root, param_lst=map_fn_lst, name="map_fn")


def read_floodmaps(
    params: dict,
    da_map_fn: str,
    idx: int,
    **kwargs,
) -> Tuple[Union[str, Path], str, str]:
    """Read names and types of flood maps. Converts to a Path object
    the path provided as String

    Parameters
    ----------
    params : dict
        Dictionary with the parameters and list of parameters used in setup_hazard.
    da_map_fn : str
        Path as string or key name in datacatalog of the hazard a specific hazard
        map idx.
    idx : int
        Index of a specific hazard map in the list of maps.

    Returns
    -------
    Tuple[Union[str, Path], str, str]
        Returns a Path or key name in datacatalog of the hazard of a specific hazard
        map idx, a string of the hazard map file name, and a string of the hazard type

    Raises
    ------
    ValueError
        Rises an error in case a netcdf file is provided withouth indicating the
        name of the layer
    """

    # load dictionary variables
    chunks = params["chunks"]
    var = params["var"]
    map_fn_lst = params["map_fn_lst"]
    map_type_lst = params["map_type_lst"]

    # Check if it is a path or a name from the catalog
    if os.path.exists(da_map_fn):
        da_map_fn = Path(da_map_fn)
        da_name = da_map_fn.stem
        da_suffix = da_map_fn.suffix
    else:
        da_name = da_map_fn

    da_type = get_param(map_type_lst, map_fn_lst, "hazard", da_name, idx, "map type")

    # Get the local hazard map.
    kwargs.update(chunks=chunks if chunks == "auto" else params["chunks_lst"][idx])

    if "da_suffix" in locals() and da_suffix == ".nc":
        if var is None:
            raise ValueError(
                "The 'var' parameter is required when reading NetCDF data."
            )
        da_var = get_param(
            params["var_lst"],
            map_fn_lst,
            "hazard",
            da_name,
            idx,
            "NetCDF variable",
        )
        kwargs.update(variables=da_var)

    return da_map_fn, da_name, da_type

def load_floodmaps(
    data_catalog: DataCatalog,
    region: gpd.GeoDataFrame,
    da_map_fn: Union[str, Path],
    da_name: str,
    name_catalog: str = "flood_maps",
    **kwargs,
) -> xr.DataArray:
    """Load flood maps in memory from datacatalog or a local path

    Parameters
    ----------
    data_catalog : DataCatalog
        Data catalog object from model.
    region : gpd.GeoDataFrame
        Region of the model.
    da_map_fn : Union[str, Path]
        Path as string or key name in datacatalog of the hazard a specific hazard
        map idx.
    da_name : str
        File name of a specific hazard map.
    name_catalog : str, optional
        Name of data catalog item to take the flood maps from, by default "flood_maps".

    Returns
    -------
    xr.DataArray
        Hazard map to be loaded to the model's maps
    """

    # reading from path
    if da_map_fn.stem:
        if da_map_fn.stem == "sfincs_map":
            sfincs_root = os.path.dirname(da_map_fn)
            sfincs_model = SfincsModel(sfincs_root, mode="r")
            sfincs_model.read_results()
            # result_list = list(sfincs_model.results.keys())
            # sfincs_model.write_raster("results.zsmax", compress="LZW")
            da = sfincs_model.results["zsmax"]
            da.encoding["_FillValue"] = None
        else:
            if not region.empty:
                da = data_catalog.get_rasterdataset(da_map_fn, geom=region, **kwargs)
            else:
                da = data_catalog.get_rasterdataset(da_map_fn, **kwargs)
    # reading from the datacatalog
    else:
        if not region.empty:
            da = data_catalog.get_rasterdataset(
                name_catalog, variables=da_name, geom=region
            )
        else:
            da = data_catalog.get_rasterdataset(name_catalog, variables=da_name)

    return da

# def load_floodmaps(
#     data_catalog: DataCatalog,
#     region: gpd.GeoDataFrame,
#     da_map_fn: Union[str, Path],
#     da_name: str,
#     name_catalog: str = "flood_maps",
#     **kwargs,
# ) -> xr.DataArray:
#     """Load flood maps in memory from datacatalog or a local path

#     Parameters
#     ----------
#     data_catalog : DataCatalog
#         Data catalog object from model.
#     region : gpd.GeoDataFrame
#         Region of the model.
#     da_map_fn : Union[str, Path]
#         Path as string or key name in datacatalog of the hazard a specific hazard
#         map idx.
#     da_name : str
#         File name of a specific hazard map.
#     name_catalog : str, optional
#         Name of data catalog item to take the flood maps from, by default "flood_maps".

#     Returns
#     -------
#     xr.DataArray
#         Hazard map to be loaded to the model's maps
#     """

#     # reading from path
#     if da_map_fn.stem:
#         if da_map_fn.stem == "sfincs_map":
#             sfincs_root = os.path.dirname(da_map_fn)
#             sfincs_model = SfincsModel(sfincs_root, mode="r")
#             sfincs_model.read_results()
#             # result_list = list(sfincs_model.results.keys())
#             # sfincs_model.write_raster("results.zsmax", compress="LZW")
#             da = sfincs_model.results["zsmax"]
#             da.encoding["_FillValue"] = None
#         else:
#             if not region.empty:
#                 da = data_catalog.get_rasterdataset(da_map_fn, geom=region, **kwargs)
#             else:
#                 da = data_catalog.get_rasterdataset(da_map_fn, **kwargs)
#     # reading from the datacatalog
#     else:
#         if not region.empty:
#             da = data_catalog.get_rasterdataset(
#                 name_catalog, variables=da_name, geom=region
#             )
#         else:
#             da = data_catalog.get_rasterdataset(name_catalog, variables=da_name)

#     return da


def check_maps_metadata(
    maps: xr.Dataset,
    params: dict,
    da: xr.DataArray,
    da_name: str,
    idx: int,
):
    """Check projection, null data and grids of a hazard map

    Parameters
    ----------
    maps : xr.Dataset
        Dataset where the maps are saved.
    params : dict
        Dictionary with the parameters and list of parameters used in setup_hazard.
    da : xr.DataArray
        Hazard map to be loaded to the model's maps.
    da_name : str
        File name of a specific hazard map.
    idx : int
        Index of a specific hazard map in the list of maps.

    Raises
    ------
    ValueError
        Error in case the hazard map has no coordinate reference system assigned.
    ValueError
        Error in case the hazard map has no nodata value assigned.
    ValueError
        Error in case the hazard maps should have identical grids.
    """

    map_fn_lst = params["map_fn_lst"]
    crs = params["crs"]
    nodata = params["nodata"]

    # Set the coordinate reference system.
    if crs is not None:
        da_crs = get_param(
            params["crs_lst"],
            map_fn_lst,
            "hazard",
            da_name,
            idx,
            "coordinate reference system",
        )
        da_crs_str = da_crs if "EPSG" in da_crs else f"EPSG:{da_crs}"
        da.raster.set_crs(da_crs_str)
    elif crs is None and not da.raster.crs:
        raise ValueError("The hazard map has no coordinate reference system assigned.")

    # Set nodata and mask the nodata value.
    if nodata is not None:
        da_nodata = get_param(
            params["nodata_lst"], map_fn_lst, "hazard", da_name, idx, "nodata"
        )
        da.raster.set_nodata(nodata=da_nodata)
    elif nodata is None and da.raster.nodata is None:
        raise ValueError("The hazard map has no nodata value assigned.")

    # Correct (if necessary) the grid orientation from the lower to the upper left corner.
    # This check could not be implemented into the sfincs_map outputs. They require to be transformed to geotiff first
    # if da_name != "sfincs_map":
    if da.raster.res[1] > 0:
        da = da.reindex({da.raster.y_dim: list(reversed(da.raster.ycoords))})

    # Check if the obtained hazard map is identical.
    if maps and not maps.raster.identical_grid(da):
        raise ValueError("The hazard maps should have identical grids.")


def check_maps_rp(
    params: dict,
    da: xr.DataArray,
    da_name: str,
    idx: int,
    risk_output: bool,
) -> list:
    """Check or retrieve return periods from file name in case risk analysis is
    performed (risk_output = True)

    Parameters
    ----------
    params : dict
        Dictionary with the parameters and list of parameters used in setup_hazard.
    da : xr.DataArray
        Hazard map to be loaded to the model's maps.
    da_name : str
        File name of a specific hazard map.
    idx : int
        Index of a specific hazard map in the list of maps.
    risk_output : bool
        The parameter that defines if a risk analysis is required.

    Returns
    -------
    list
        List containing the return of each hazard map in case a risk analysis is
        required

    Raises
    ------
    ValueError
        Error in case return period could not be derived from the file's names
    ValueError
        Error in are not provided and they could not be derived from the file's
        names
    """

    map_fn_lst = params["map_fn_lst"]

    # Get the return period input parameter.
    if "rp_lst" in params:
        da_rp = get_param(
            params["rp_lst"],
            map_fn_lst,
            "hazard",
            da_name,
            idx,
            "return period",
        )
    else:
        da_rp = None

    if risk_output:
        da = da.expand_dims({"rp": [da_rp]}, axis=0)

    if risk_output and da_rp is None:
        # Get (if possible) the return period from dataset names if the input parameter is None.
        if "rp" in da_name.lower():

            def fstrip(x):
                return x in "0123456789."

            rp_str = "".join(filter(fstrip, da_name.lower().split("rp")[-1])).lstrip(
                "0"
            )

            try:
                assert isinstance(
                    literal_eval(rp_str) if rp_str else None, (int, float)
                )
                da_rp = literal_eval(rp_str)

            except AssertionError:
                raise ValueError(
                    f"Could not derive the return period for hazard map: {da_name}."
                )
        else:
            raise ValueError(
                "The hazard map must contain a return period in order to conduct a risk calculation."
            )

    return da_rp


def check_map_uniqueness(
    map_name_lst: list,
):
    """Check if the provided maps are unique

    Parameters
    ----------
    map_name_lst : list
        List containing the names of the maps loaded into the model
    """
    check_uniqueness(map_name_lst)


# old version of check_maps_uniquenes
# def check_maps_uniquenes(
#     get_config,
#     maps: xr.Dataset,
#     params: dict,
#     da: xr.DataArray,
#     da_map_fn: Union[str, Path],
#     da_name: str,
#     da_type: str,
#     da_rp: Union[int, float],
#     idx: int,
# ):

#     chunks         = params['chunks']

#     # Add the hazard map to config and staticmaps.
#     check_uniqueness(
#         get_config,
#         maps,
#         "hazard",
#         da_type,
#         da_name,
#         {
#             "usage": True,
#             "map_fn": da_map_fn,
#             "map_type": da_type,
#             "rp": da_rp,
#             "crs": da.raster.crs,
#             "nodata": da.raster.nodata,
#             # "var": None if "var_lst" not in locals() else self.var_lst[idx],
#             "var": None if not 'var_lst' in params else params['var_lst'][idx],
#             "chunks": "auto" if chunks == "auto" else params['chunks_lst'][idx],
#         },
#         file_type="hazard",
#         filename=da_name,
#     )


def check_floodmaps(
    get_config,
    maps,
    params,
    da,
    da_map_fn,
    da_name,
    da_type,
    idx,
    risk_output,
    **kwargs,
):
    map_fn_lst = params["map_fn_lst"]
    chunks = params["chunks"]
    crs = params["crs"]
    nodata = params["nodata"]

    # Set the coordinate reference system.
    if crs is not None:
        da_crs = get_param(
            params["crs_lst"],
            map_fn_lst,
            "hazard",
            da_name,
            idx,
            "coordinate reference system",
        )
        da_crs_str = da_crs if "EPSG" in da_crs else f"EPSG:{da_crs}"
        da.raster.set_crs(da_crs_str)
    elif crs is None and not da.raster.crs:
        raise ValueError("The hazard map has no coordinate reference system assigned.")

    # Set nodata and mask the nodata value.
    if nodata is not None:
        da_nodata = get_param(
            params["nodata_lst"], map_fn_lst, "hazard", da_name, idx, "nodata"
        )
        da.raster.set_nodata(nodata=da_nodata)
    elif nodata is None and da.raster.nodata is None:
        raise ValueError("The hazard map has no nodata value assigned.")

    # Correct (if necessary) the grid orientation from the lower to the upper left corner.
    # This check could not be implemented into the sfincs_map outputs. They require to be transformed to geotiff first
    # if da_name != "sfincs_map":
    if da.raster.res[1] > 0:
        da = da.reindex({da.raster.y_dim: list(reversed(da.raster.ycoords))})

    # Check if the obtained hazard map is identical.
    if maps and not maps.raster.identical_grid(da):
        raise ValueError("The hazard maps should have identical grids.")

    # Get the return period input parameter.
    if "rp_lst" in params:
        da_rp = get_param(
            params["rp_lst"],
            map_fn_lst,
            "hazard",
            da_name,
            idx,
            "return period",
        )
    else:
        da_rp = None

    if risk_output:
        da = da.expand_dims({"rp": [da_rp]}, axis=0)

    if risk_output and da_rp is None:
        # Get (if possible) the return period from dataset names if the input parameter is None.
        if "rp" in da_name.lower():

            def fstrip(x):
                return x in "0123456789."

            rp_str = "".join(filter(fstrip, da_name.lower().split("rp")[-1])).lstrip(
                "0"
            )

            try:
                assert isinstance(
                    literal_eval(rp_str) if rp_str else None, (int, float)
                )
                da_rp = literal_eval(rp_str)

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
        get_config,
        maps,
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
            "var": None if "var_lst" not in params else params["var_lst"][idx],
            "chunks": "auto" if chunks == "auto" else params["chunks_lst"][idx],
        },
        file_type="hazard",
        filename=da_name,
    )
    return da_rp
