"""Main module."""

from pathlib import Path
from typing import Any, Dict, List, Union

import xarray as xr
from hydromt import Model, hydromt_step


class FIATModel(Model):
    """Read or Write a FIAT model.

    Parameters
    ----------
    root : str, optional
        Model root, by default None
    components: Dict[str, Any], optional
        Dictionary of components to add to the model, by default None
        Every entry in this dictionary contains the name of the component as key,
        and the component object as value, or a dictionary with options passed
        to the component initializers.
        If a component is a dictionary, the key 'type' should be provided with the
        name of the component type.

        .. code-block:: python

            {
                "grid": {
                    "type": "GridComponent",
                    "filename": "path/to/grid.nc"
                }
            }

    mode : {'r','r+','w'}, optional
        read/append/write mode, by default "w"
    data_libs : List[str], optional
        List of data catalog configuration files, by default None
    region_component : str, optional
        The name of the region component in the components dictionary.
        If None, the model will can automatically determine the region component
        if there is only one `SpatialModelComponent`.
        Otherwise it will raise an error.
        If there are no `SpatialModelComponent` it will raise a warning
        that `region` functionality will not work.
    logger:
        The logger to be used.
    **catalog_keys:
        Additional keyword arguments to be passed down to the DataCatalog.
    """

    def __init__(
        self,
        root: str | None = None,
        *,
        components: Dict[str, Any] | None = None,
        mode: str = "w",
        data_libs: Union[List, str] | None = None,
        region_component: str | None = None,
        **catalog_keys,
    ):
        Model.__init__(
            self,
            root,
            components=components,
            mode=mode,
            data_libs=data_libs,
            region_component=region_component,
            **catalog_keys,
        )

    @hydromt_step
    def setup_hazard(
        self,
        hazard_fname: Path | str | list[Path | str],
        risk: bool = False,
        return_periods: list[int] | None = None,
        hazard_type: str | None = "flooding",
    ):
        """Set up hazard maps."""
        if not isinstance(hazard_fname, list):
            hazard_fname = [hazard_fname]
        if risk and not return_periods:
            raise ValueError("Cannot perform risk analysis without return periods")
        if risk and len(return_periods) != len(hazard_fname):
            raise ValueError("Return periods do not match the number of hazard files")
        hazard_dataarrays = []

        # Get components from model
        grid = self.get_component("hazard_grid")
        config = self.get_component("config")

        for i, hazard_file in enumerate(hazard_fname):
            hazard_file = Path(hazard_file)
            if not hazard_file.exists:
                raise ValueError("Hazard file name must be a valid path")

            da = self.data_catalog.get_rasterdataset(hazard_file)

            # Convert to gdal compliant
            da.encoding["_FillValue"] = None
            da: xr.DataArray = da.raster.gdal_compliant()

            # ensure variable name is lowercase
            da_name = hazard_file.stem.lower()
            da = da.rename(da_name)

            # Check if map is rotated and if yes, reproject to a non-rotated grid
            if "xc" in da.coords:
                self.logger.warning(
                    "Hazard map is rotated. It will be reprojected"
                    " to a none rotated grid using nearest neighbor"
                    "interpolation"
                )
                da: xr.DataArray = da.raster.reproject(dst_crs=da.rio.crs)
            if "grid_mapping" in da.encoding:
                del da.encoding["grid_mapping"]

            rp = f"(rp {return_periods[i]})" if risk else ""
            self.logger.info(f"Added {hazard_type} hazard map: {da_name} {rp}")

            if not risk:
                # Set the event data arrays to the hazard grid component
                da = da.assign_attrs(
                    {
                        "name": da_name,
                        "type": hazard_type,
                        "analysis": "event",
                    }
                )
                grid.set(da)

            hazard_dataarrays.append(da)

        if risk:
            ds = xr.merge(hazard_dataarrays)
            da_names = [d.name for d in hazard_dataarrays]
            ds = ds.assign_attrs(
                {
                    "return_period": return_periods,
                    "type": hazard_type,
                    "name": da_names,
                    "analysis": "risk",
                }
            )
            config.set("risk", risk)
            config.set("hazard.return_periods", return_periods)
            grid.set(ds)

        config.set("hazard.file", grid._filename)
        config.set(
            "hazard.elevation_reference",
            "DEM" if hazard_type == "water_depth" else "datum",
        )
