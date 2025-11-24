"""The hazard component."""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import xarray as xr
from hydromt._io.writers import _write_nc
from hydromt.model import Model
from hydromt.model.components import GridComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.utils import (
    GRID,
    HAZARD,
    HAZARD_FILE,
    HAZARD_RP,
    HAZARD_SETTINGS,
    MODEL_RISK,
    REGION,
    SRS,
    VAR_AS_BAND,
    srs_representation,
)

__all__ = ["HazardComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class HazardComponent(GridComponent):
    """Hazard component.

    Inherits from the HydroMT-core GridComponent model-component.

    Parameters
    ----------
    model : Model
        HydroMT model instance (FIATModel).
    filename : str, optional
        The path to use for reading and writing of component data by default.
        By default "hazard.nc".
    region_component : str, optional
        The name of the region component to use as reference
        for this component's region. If None, the region will be set to the grid extent.
        Note that the create method only works if the region_component is None.
        For add_data_from_* methods, the other region_component should be
        a reference to another grid component for correct reprojection, by default None.
    region_filename : str
        The path to use for reading and writing of the region data by default.
        By default "region.geojson".
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = f"{HAZARD}.nc",
        region_component: str | None = None,
        region_filename: str = f"{REGION}.geojson",
    ):
        super().__init__(
            model,
            filename=filename,
            region_component=region_component,
            region_filename=region_filename,
        )

    ## I/O methods
    @hydromt_step
    def read(
        self,
        filename: str | None = None,
        **kwargs,
    ) -> None:
        """Read the hazard data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root. If None, the value is either taken from
            the model configurations or the `_filename` attribute, by default None.
        **kwargs : dict
            Additional keyword arguments to be passed to the `read_nc` method.
        """
        # Sort the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = (
            filename
            or self.model.config.get(HAZARD_FILE, abs_path=True)
            or self._filename
        )
        # Read the data
        logger.info("Reading the hazard data..")
        super().read(filename=filename, **kwargs)

    @hydromt_step
    def write(
        self,
        filename: str | None = None,
        gdal_compliant: bool = True,
        **kwargs,
    ) -> None:
        """Write the hazard data.

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root. If None, the value is either taken from
            the model configurations or the `_filename` attribute, by default None.
        gdal_compliant : bool, optional
            If True, write grid data in a way that is compatible with GDAL,
            by default True.
        **kwargs : dict
            Additional keyword arguments to be passed to the `write_nc` method.
        """
        # Check the state
        self.root._assert_write_mode()

        # Check for data. If no data, warn and return
        if len(self.data) == 0:
            logger.info("No hazard data found, skip writing.")
            return

        # Sort out the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = filename or self.model.config.get(HAZARD_FILE) or self._filename
        write_path = Path(self.root.path, filename)

        # Write it in a gdal compliant manner by default
        logger.info("Writing the hazard data..")
        _write_nc(
            {GRID: self.data},
            write_path.as_posix(),
            root=self.root.path,
            gdal_compliant=gdal_compliant,
            rename_dims=False,
            force_overwrite=self.root.mode.is_override_mode(),
            force_sn=False,
            **kwargs,
        )

        # Update the config
        self.model.config.set(HAZARD_FILE, write_path)
        # Check for multiple bands, because gdal and netcdf..
        self.model.config.set(f"{HAZARD_SETTINGS}.{VAR_AS_BAND}", False)
        if len(self.data.data_vars) > 1:
            self.model.config.set(f"{HAZARD_SETTINGS}.{VAR_AS_BAND}", True)
        # Set the srs
        self.model.config.set(
            f"{HAZARD_SETTINGS}.{SRS}",
            srs_representation(self.data.raster.crs),
        )

    ## Mutating methods
    @hydromt_step
    def clear(self):
        """Clear the hazard data."""
        self._data = None
        self._initialize_grid(skip_read=True)

    @hydromt_step
    def clip(
        self,
        geom: gpd.GeoDataFrame,
        buffer: int = 0,
        inplace: bool = False,
    ) -> xr.Dataset | None:
        """Clip the hazard data based on geometry.

        Parameters
        ----------
        geom : gpd.GeoDataFrame
            The area to clip the data to.
        buffer : int, optional
            A buffer of cells around the clipped area to keep, by default 0.
        inplace : bool, optional
            Whether to do the clipping in place or return a new xr.Dataset,
            by default False.

        Returns
        -------
        xr.Dataset | None
            Return a dataset if the inplace is False.
        """
        # Check whether it has the necessary dims
        try:
            self.data.raster.set_spatial_dims()
        except ValueError:
            return None

        # If so, clip the data
        data = self.data.raster.clip_geom(geom, buffer=buffer)
        # If inplace, just set the data and return nothing
        if inplace:
            self._data = data
            return None
        return data

    # Setup methods
    @hydromt_step
    def setup(
        self,
        hazard_fnames: list[Path | str] | Path | str,
        hazard_type: str = "water_depth",
        *,
        return_periods: list[int] | None = None,
        risk: bool = False,
        unit: str = "m",
        **settings: dict[str, Any],
    ) -> None:
        """Set up hazard maps.

        Parameters
        ----------
        hazard_fnames : list[Path | str] | Path | str
            Path(s) to the hazard file(s) or name(s) of the data catalog entries.
        hazard_type : str, optional
            Type of hazard, by default "water_depth".
        return_periods : list[int] | None, optional
            List of return periods. Length of list should match the number hazard
            files, by default None.
        risk : bool, optional
            Whether the hazard files are part of a risk analysis,
            by default False.
        unit : str, optional
            The unit which the hazard data is in, by default 'm' (meters).
        **settings : dict
            Extra settings to be added under the hazard header.

        Returns
        -------
            None
        """
        logger.info("Setting up hazard raster data")
        if not isinstance(hazard_fnames, list):
            hazard_fnames = [hazard_fnames]
        if risk and return_periods is None:
            raise ValueError("Cannot perform risk analysis without return periods")
        if (
            risk
            and return_periods is not None
            and len(return_periods) != len(hazard_fnames)
        ):
            raise ValueError("Return periods do not match the number of hazard files")

        if self.model.region is None:
            raise MissingRegionError(
                "Region component is missing for setting up hazard data."
            )

        hazard_data = {}
        for entry in hazard_fnames:
            da = self.model.data_catalog.get_rasterdataset(
                entry,
                geom=self.model.region,
            )
            hazard_data[Path(entry).stem] = da

        # Check if there is already data set to this grid component.
        grid_like = self.data if self.data.sizes != {} else None

        # Parse hazard files to an xarray dataset
        ds = workflows.hazard_setup(
            grid_like=grid_like,
            hazard_data=hazard_data,
            hazard_type=hazard_type,
            return_periods=return_periods,
            risk=risk,
            unit=unit,
        )

        # Set the data to the hazard grid component
        self.set(ds)

        # Set the config entries
        self.model.config.set(MODEL_RISK, risk)
        if risk:
            self.model.config.set(HAZARD_RP, return_periods)

        # Set the extra settings
        for key, item in settings.items():
            self.model.config.set(f"{HAZARD}.{key}", item)
