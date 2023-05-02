from hydromt_fiat.validation import Validation
from pathlib import Path
import geopandas as gpd
from ast import literal_eval


class Hazard:
    def __init__(self):
        self.crs = ""

    def setup_hazard(
        self,
        model_fiat,
        hazard_type,
        risk_output,
        map_fn,
        map_type,
        chunks="auto",
        rp=None,
        crs=None,
        nodata=None,
        var=None,
        region=gpd.GeoDataFrame(),
        **kwargs,
    ):

        check = Validation()
        # Check the hazard input parameter types.
        map_fn_lst = [map_fn] if isinstance(map_fn, (str, Path)) else map_fn
        map_type_lst = [map_type] if isinstance(map_type, (str, Path)) else map_type
        check.check_param_type(map_fn_lst, name="map_fn", types=(str, Path))
        check.check_param_type(map_type_lst, name="map_type", types=str)
        if chunks != "auto":
            chunks_lst = [chunks] if isinstance(chunks, (int, dict)) else chunks
            check.check_param_type(chunks_lst, name="chunks", types=(int, dict))
            if not len(chunks_lst) == 1 and not len(chunks_lst) == len(map_fn_lst):
                raise IndexError(
                    "The number of 'chunks' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        if rp is not None:
            rp_lst = [rp] if isinstance(rp, (int, float)) else rp
            check.check_param_type(rp_lst, name="rp", types=(float, int))
            if not len(rp_lst) == len(map_fn_lst):
                raise IndexError(
                    "The number of 'rp' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        if crs is not None:
            crs_lst = [str(crs)] if isinstance(crs, (int, str)) else crs
            check.check_param_type(crs_lst, name="crs", types=(int, str))
        if nodata is not None:
            nodata_lst = [nodata] if isinstance(nodata, (float, int)) else nodata
            check.check_param_type(nodata_lst, name="nodata", types=(float, int))
        if var is not None:
            var_lst = [var] if isinstance(var, str) else var
            check.check_param_type(var_lst, name="var", types=str)

        # Check if the hazard input files exist.
        check.check_file_exist(model_fiat.root, param_lst=map_fn_lst, name="map_fn")

        if False:
            # For return period flood maps
            # Reading from yml
            da_mutiple = model_fiat.data_catalog.get_rasterdataset("flood_maps")
            map_fn_lst = [i for i in list(da_mutiple.variables) if "RP" in i]

            # Read the hazard map(s) and add to config and staticmaps.
            for idx, da_map_fn in enumerate(map_fn_lst):
                da_name = da_map_fn
                da_type = check.get_param(
                    map_type_lst, map_fn_lst, "hazard", da_name, idx, "map type"
                )

                da = model_fiat.data_catalog.get_rasterdataset(
                    "flood_maps", variables=da_name
                )

                # Get the local hazard map.
                kwargs.update(chunks=chunks if chunks == "auto" else chunks_lst[idx])

                # Set (if necessary) the coordinate reference system.
                # if crs is not None and not da.raster.crs.is_epsg_code:
                if crs is not None and not da.raster.crs:
                    da_crs = check.get_param(
                        crs_lst,
                        map_fn_lst,
                        "hazard",
                        da_name,
                        idx,
                        "coordinate reference system",
                    )
                    da_crs_str = da_crs if "EPSG" in da_crs else f"EPSG:{da_crs}"
                    da.raster.set_crs(da_crs_str)
                # elif crs is None and not da.raster.crs.is_epsg_code:
                elif crs is None and not da.raster.crs:
                    raise ValueError(
                        "The hazard map has no coordinate reference system assigned."
                    )

                # Set (if necessary) and mask the nodata value.
                if nodata is not None:
                    da_nodata = check.get_param(
                        nodata_lst, map_fn_lst, "hazard", da_name, idx, "nodata"
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
                    check.get_param(
                        rp_lst, map_fn_lst, "hazard", da_name, idx, "return period"
                    )
                    if "rp_lst" in locals()
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
                        except AssertionError:
                            raise ValueError(
                                f"Could not derive the return period for hazard map: {da_name}."
                            )
                    else:
                        raise ValueError(
                            "The hazard map must contain a return period in order to conduct a risk calculation."
                        )

                # Add the hazard map to config and staticmaps.
                check.check_uniqueness(
                    model_fiat,
                    "hazard",
                    da_type,
                    da_name,
                    {
                        "usage": True,
                        # "map_fn": da_map_fn,
                        "map_type": da_type,
                        "rp": da_rp,
                        "crs": da.raster.crs,
                        "nodata": da.raster.nodata,
                        "var": None if "var_lst" not in locals() else var_lst[idx],
                        "chunks": "auto" if chunks == "auto" else chunks_lst[idx],
                    },
                    file_type="hazard",
                    filename=da_name,
                )

                model_fiat.set_config(
                    "hazard",
                    da_type,
                    da_name,
                    {
                        "usage": "True",
                        # "map_fn": da_map_fn,
                        "map_type": da_type,
                        "rp": da_rp,
                        "crs": da.raster.crs,
                        "nodata": da.raster.nodata,
                        "var": None if "var_lst" not in locals() else var_lst[idx],
                        "chunks": "auto" if chunks == "auto" else chunks_lst[idx],
                    },
                )

                model_fiat.set_staticmaps(da, da_name)
                post = f"(rp {da_rp})" if rp is not None and risk_output else ""
                model_fiat.logger.info(
                    f"Added {hazard_type} hazard map: {da_name} {post}"
                )

        if True:
            # For a single event and with previous hydromt_fiat version
            # Read the hazard map(s) and add to config and staticmaps.
            for idx, da_map_fn in enumerate(map_fn_lst):
                if da_map_fn not in model_fiat.data_catalog:
                    da_map_fn = Path(da_map_fn)
                    da_name = da_map_fn.stem
                    da_suffix = da_map_fn.suffix
                else:
                    da_name = Path(model_fiat.data_catalog[da_map_fn].path).stem
                    da_suffix = Path(model_fiat.data_catalog[da_map_fn].path).suffix

                da_type = check.get_param(
                    map_type_lst, map_fn_lst, "hazard", da_name, idx, "map type"
                )

                # Get the local hazard map.
                kwargs.update(chunks=chunks if chunks == "auto" else chunks_lst[idx])
                if da_suffix == ".nc":
                    if var is None:
                        raise ValueError(
                            "The 'var' parameter is required when reading NetCDF data."
                        )
                    kwargs.update(
                        variables=check.get_param(
                            var_lst,
                            map_fn_lst,
                            "hazard",
                            da_name,
                            idx,
                            "NetCDF variable",
                        )
                    )
                # The previous function can only work if .region is recognized. Set_basemap must be applied.
                if not region.empty:
                    da = model_fiat.data_catalog.get_rasterdataset(
                        da_map_fn, geom=region, **kwargs
                    )
                else:
                    da = model_fiat.data_catalog.get_rasterdataset(da_map_fn, **kwargs)

                # Set (if necessary) the coordinate reference system.
                # if crs is not None and not da.raster.crs.is_epsg_code:
                if crs is not None and not da.raster.crs:
                    da_crs = check.get_param(
                        crs_lst,
                        map_fn_lst,
                        "hazard",
                        da_name,
                        idx,
                        "coordinate reference system",
                    )
                    da_crs_str = da_crs if "EPSG" in da_crs else f"EPSG:{da_crs}"
                    da.raster.set_crs(da_crs_str)
                    self.crs = da_crs_str

                # elif crs is None and not da.raster.crs.is_epsg_code:
                elif crs is None and not da.raster.crs:
                    raise ValueError(
                        "The hazard map has no coordinate reference system assigned."
                    )

                # TODO: the function set_nodata seems to be depricated. Decide if we need this functionality.
                # Set (if necessary) and mask the nodata value.
                # if nodata is not None:
                #     da_nodata = check.get_param(
                #         nodata_lst, map_fn_lst, "hazard", da_name, idx, "nodata"
                #     )
                #     da.raster.set_nodata(nodata=da_nodata)
                # elif nodata is None and da.raster.nodata is None:
                #     raise ValueError("The hazard map has no nodata value assigned.")

                # Correct (if necessary) the grid orientation from the lower to the upper left corner.
                if da.raster.res[1] > 0:
                    da = da.reindex(
                        {da.raster.y_dim: list(reversed(da.raster.ycoords))}
                    )

                # Check if the obtained hazard map is identical.
                if model_fiat.maps and not model_fiat.maps.raster.identical_grid(da):
                    raise ValueError("The hazard maps should have identical grids.")

                # Get the return period input parameter.
                da_rp = (
                    check.get_param(
                        rp_lst, map_fn_lst, "hazard", da_name, idx, "return period"
                    )
                    if "rp_lst" in locals()
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
                        except AssertionError:
                            raise ValueError(
                                f"Could not derive the return period for hazard map: {da_name}."
                            )
                    else:
                        raise ValueError(
                            "The hazard map must contain a return period in order to conduct a risk calculation."
                        )

                # Add the hazard map to config and staticmaps.
                check.check_uniqueness(
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
                        "var": None if "var_lst" not in locals() else var_lst[idx],
                        "chunks": "auto" if chunks == "auto" else chunks_lst[idx],
                    },
                    file_type="hazard",
                    filename=da_name,
                )

                model_fiat.set_config(
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
                        "var": None if "var_lst" not in locals() else var_lst[idx],
                        "chunks": "auto" if chunks == "auto" else chunks_lst[idx],
                    },
                )

                model_fiat.set_maps(da, da_name)
                post = f"(rp {da_rp})" if rp is not None and risk_output else ""
                model_fiat.logger.info(
                    f"Added {hazard_type} hazard map: {da_name} {post}"
                )
