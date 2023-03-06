from ast import literal_eval

### TO BE UPDATED ###
class Hazard:
    def setup_hazard(
        self,
        map_fn,
        map_type,
        chunks="auto",
        rp=None,
        crs=None,
        nodata=None,
        var=None,
        **kwargs,
    ):
        """Add a hazard map to the FIAT model schematization.

        Adds model layer:

        * **hazard** map(s): A raster map with the nomenclature <file_name>.

        Parameters
        ----------
        map_fn: (list of) str, Path
            Absolute or relative (with respect to the configuration file or hazard directory) path to the hazard file.
        map_type: (list of) str
            Description of the hazard type.
        rp: (list of) int, float, optional
            Return period in years, required for a risk calculation.
        crs: (list of) int, str, optional
            Coordinate reference system of the hazard file.
        nodata: (list of) int, float, optional
            Value that is assigned as nodata.
        var: (list of) str, optional
            Hazard variable name in NetCDF input files.
        chunks: (list of) int, optional
            Chunk sizes along each dimension used to load the hazard file into a dask array. The default is value 'auto'.
        """

        # Check the hazard input parameter types.
        map_fn_lst = [map_fn] if isinstance(map_fn, (str, Path)) else map_fn
        map_type_lst = [map_type] if isinstance(map_type, (str, Path)) else map_type
        self.check_param_type(map_fn_lst, name="map_fn", types=(str, Path))
        self.check_param_type(map_type_lst, name="map_type", types=str)
        if chunks != "auto":
            chunks_lst = [chunks] if isinstance(chunks, (int, dict)) else chunks
            self.check_param_type(chunks_lst, name="chunks", types=(int, dict))
            if not len(chunks_lst) == 1 or not len(chunks_lst) == len(map_fn_lst):
                raise IndexError(
                    "The number of 'chunks' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        if rp is not None:
            rp_lst = [rp] if isinstance(rp, (int, float)) else rp
            self.check_param_type(rp_lst, name="rp", types=(float, int))
            if not len(rp_lst) == len(map_fn_lst):
                raise IndexError(
                    "The number of 'rp' parameters should match with the number of "
                    "'map_fn' parameters."
                )
        if crs is not None:
            crs_lst = [str(crs)] if isinstance(crs, (int, str)) else crs
            self.check_param_type(crs_lst, name="crs", types=(int, str))
        if nodata is not None:
            nodata_lst = [nodata] if isinstance(nodata, (float, int)) else nodata
            self.check_param_type(nodata_lst, name="nodata", types=(float, int))
        if var is not None:
            var_lst = [var] if isinstance(var, str) else var
            self.check_param_type(var_lst, name="var", types=str)

        # Check if the hazard input files exist.
        self.check_file_exist(map_fn_lst, name="map_fn")

        # Read the hazard map(s) and add to config and staticmaps.
        for idx, da_map_fn in enumerate(map_fn_lst):
            da_name = da_map_fn.stem
            da_type = self.get_param(
                map_type_lst, map_fn_lst, "hazard", da_name, idx, "map type"
            )

            # Get the local hazard map.
            kwargs.update(chunks=chunks if chunks == "auto" else chunks_lst[idx])
            if da_map_fn.suffix == ".nc":
                if var is None:
                    raise ValueError(
                        "The 'var' parameter is required when reading NetCDF data."
                    )
                kwargs.update(
                    variables=self.get_param(
                        var_lst, map_fn_lst, "hazard", da_name, idx, "NetCDF variable"
                    )
                )
            da = self.data_catalog.get_rasterdataset(
                da_map_fn, geom=self.region, **kwargs
            )

            # Set (if necessary) the coordinate reference system.
            if crs is not None and not da.raster.crs.is_epsg_code:
                da_crs = self.get_param(
                    crs_lst,
                    map_fn_lst,
                    "hazard",
                    da_name,
                    idx,
                    "coordinate reference system",
                )
                da_crs_str = da_crs if "EPSG" in da_crs else f"EPSG:{da_crs}"
                da.raster.set_crs(da_crs_str)
            elif crs is None and not da.raster.crs.is_epsg_code:
                raise ValueError(
                    "The hazard map has no coordinate reference system assigned."
                )

            # Set (if necessary) and mask the nodata value.
            if nodata is not None:
                da_nodata = self.get_param(
                    nodata_lst, map_fn_lst, "hazard", da_name, idx, "nodata"
                )
                da.raster.set_nodata(nodata=da_nodata)
            elif nodata is None and da.raster.nodata is None:
                raise ValueError("The hazard map has no nodata value assigned.")

            # Correct (if necessary) the grid orientation from the lower to the upper left corner.
            if da.raster.res[1] > 0:
                da = da.reindex({da.raster.y_dim: list(reversed(da.raster.ycoords))})

            # Check if the obtained hazard map is identical.
            if self.staticmaps and not self.staticmaps.raster.identical_grid(da):
                raise ValueError("The hazard maps should have identical grids.")

            # Get the return period input parameter.
            da_rp = (
                self.get_param(
                    rp_lst, map_fn_lst, "hazard", da_name, idx, "return period"
                )
                if "rp_lst" in locals()
                else None
            )
            if self.get_config("risk_output") and da_rp is None:

                # Get (if possible) the return period from dataset names if the input parameter is None.
                if "rp" in da_name.lower():
                    fstrip = lambda x: x in "0123456789."
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
            hazard_type = self.get_config("hazard_type", fallback="flooding")
            self.check_uniqueness(
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
            self.set_config(
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
            self.set_staticmaps(da, da_name)
            post = (
                f"(rp {da_rp})"
                if rp is not None and self.get_config("risk_output")
                else ""
            )
            self.logger.info(f"Added {hazard_type} hazard map: {da_name} {post}")

    def get_param(self, param_lst, map_fn_lst, file_type, filename, i, param_name):
        """ """

        if len(param_lst) == 1:
            return param_lst[0]
        elif len(param_lst) != 1 and len(map_fn_lst) == len(param_lst):
            return param_lst[i]
        elif len(param_lst) != 1 and len(map_fn_lst) != len(param_lst):
            raise IndexError(
                f"Could not derive the {param_name} parameter for {file_type} "
                f"map: {filename}."
            )
        
    def check_param_type(self, param, name=None, types=None):
        """ """

        if not isinstance(param, list):
            raise TypeError(
                f"The '{name}_lst' parameter should be a of {list}, received a "
                f"{type(param)} instead."
            )
        for i in param:
            if not isinstance(i, types):
                if isinstance(types, tuple):
                    types = " or ".join([str(j) for j in types])
                else:
                    types = types
                raise TypeError(
                    f"The '{name}' parameter should be a of {types}, received a "
                    f"{type(i)} instead."
                )
