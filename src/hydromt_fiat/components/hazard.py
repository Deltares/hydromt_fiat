"""The hazard component."""

import logging
from pathlib import Path
from typing import Any

from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components.grid import GridComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.gis.raster import expand_raster_to_bounds
from hydromt_fiat.gis.utils import crs_representation
from hydromt_fiat.readers import read_grid
from hydromt_fiat.utils import (
    HAZARD,
    HAZARD_FILE,
    HAZARD_RP,
    HAZARD_SETTINGS,
    MODEL_RISK,
    SRS,
    VAR_AS_BAND,
)
from hydromt_fiat.writers import write_grid

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
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = f"{HAZARD}.nc",
        region_component: str | None = None,
    ):
        self._filename = filename
        super().__init__(
            model,
            region_component=region_component,
        )

    ## I/O methods
    @hydromt_step
    def read(
        self,
        filename: Path | str | None = None,
        **kwargs,
    ) -> None:
        """Read the hazard data.

        Parameters
        ----------
        filename : Path | str, optional
            Filename relative to model root. If None, the value is either taken from
            the model configurations or the `_filename` attribute, by default None.
        **kwargs : dict
            Additional keyword arguments to be passed to the `open_dataset` function
            from xarray.
        """
        # Check the state
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = (
            filename
            or self.model.config.get(HAZARD_FILE, abs_path=True)
            or self._filename
        )

        # Read the data
        read_path = Path(self.root.path, filename)
        # Return on nothing found
        if not read_path.is_file():
            return
        logger.info("Reading hazard data")
        # Read with the simple read function
        ds = read_grid(read_path=read_path, **kwargs)
        # Set the dataset
        self.set(ds)

    @hydromt_step
    def write(
        self,
        filename: Path | str | None = None,
        gdal_compliant: bool = True,
        **kwargs,
    ) -> None:
        """Write the hazard data.

        Parameters
        ----------
        filename : Path | str, optional
            Filename relative to model root. If None, the value is either taken from
            the model configurations or the `_filename` attribute, by default None.
        gdal_compliant : bool, optional
            If True, write grid data in a way that is compatible with GDAL,
            by default True.
        **kwargs : dict
            Additional keyword arguments to be passed to the `to_netcdf` method from
            xarray.
        """
        # Check the state
        self.root._assert_write_mode()

        # Check for data. If no data, warn and return
        if len(self.data) == 0:
            logger.info("No hazard data found, skip writing")
            return

        # Sort out the filename
        # Hierarchy: 1) signature, 2) config file, 3) default
        filename = filename or self.model.config.get(HAZARD_FILE) or self._filename
        write_path = Path(self.root.path, filename)

        # Write it in a gdal compliant manner by default
        logger.info("Writing hazard data")
        write_grid(
            data=self.data,
            write_path=write_path,
            gdal_compliant=gdal_compliant,
            overwrite=self.root.mode.is_override_mode(),
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
            crs_representation(self.data.raster.crs),
        )

    # Setup methods
    @hydromt_step
    def create(
        self,
        hazard_fnames: list[Path | str] | Path | str,
        hazard_type: str = "water_depth",
        *,
        return_periods: list[int] | None = None,
        risk: bool = False,
        unit: str = "m",
        expand: bool = True,
        region: bool = True,
        read_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Create hazard maps from data sources.

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
        expand : bool, optional
            Whether to expand the hazard data to the bounding box of the model region.
            Nothing is done when the hazard data already covers the region.
            By default True.
        region : bool, optional
            Whether or not to use the model region. By default True.
        read_kwargs : dict, optional
            Optional keyword arguments for reading the `hazard_fnames` data. These
            arguments are passed to the HydroMT
            :py:meth:`~hydromt.DataCatalog.get_rasterdataset` method. By default None.

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

        if self.model.region is None and region:
            raise MissingRegionError(
                "Region component is missing for setting up hazard data"
            )

        # Read the data
        hazard_data = {}
        kwargs = {"buffer": 1}
        kwargs.update(read_kwargs or {})
        # Loop over the entries
        for entry in hazard_fnames:
            da = self.model.data_catalog.get_rasterdataset(
                entry,
                geom=self.model.region,
                **kwargs,
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

        # Expand if necessary
        if self.model.region is not None and ds.raster.crs is not None and expand:
            ds = expand_raster_to_bounds(
                ds=ds,
                bbox=self.model.region.to_crs(da.raster.crs).total_bounds,
            )

        # Set the data to the hazard grid component
        self.set(ds)

        # Set the config entries
        self.model.config.set(MODEL_RISK, risk)
        if risk:
            self.model.config.set(HAZARD_RP, return_periods)
