"""The custom hazard component."""

import logging
from pathlib import Path

from hydromt.model import Model
from hydromt.model.components import GridComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.errors import MissingRegionError

__all__ = ["HazardGridComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class HazardGridComponent(GridComponent):
    """Custom hazard component.

    Inherits from the HydroMT-core GridComponent model-component.

    Parameters
    ----------
    model: Model
        HydroMT model instance
    filename: str
        The path to use for reading and writing of component data by default.
        By default "hazard/hazard_grid.nc".
    region_component: str, optional
        The name of the region component to use as reference
        for this component's region. If None, the region will be set to the grid extent.
        Note that the create method only works if the region_component is None.
        For add_data_from_* methods, the other region_component should be
        a reference to another grid component for correct reprojection, by default None
    region_filename: str
        The path to use for reading and writing of the region data by default.
        By default "region.geojson".
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = "hazard/hazard_grid.nc",
        region_component: str | None = None,
        region_filename: str = "region.geojson",
    ):
        GridComponent.__init__(
            self,
            model,
            filename=filename,
            region_component=region_component,
            region_filename=region_filename,
        )

    @hydromt_step
    def setup_hazard(
        self,
        hazard_fnames: list[Path | str] | Path | str,
        hazard_type: str = "flooding",
        *,
        return_periods: list[int] | None = None,
        risk: bool = False,
        unit: str = "m",
    ) -> None:
        """Set up hazard maps.

        Parameters
        ----------
        hazard_fnames : list[Path | str] | Path | str
            Path(s) to the hazard file(s) or name(s) of the data catalog entries.
        hazard_type : str, optional
            Type of hazard, by default "flooding".
        return_periods : list[int] | None, optional
            List of return periods. Length of list should match the number hazard
            files, by default None.
        risk : bool, optional
            Whether the hazard files are part of a risk analysis,
            by default False.
        unit : str, optional
            The unit which the hazard data is in, by default 'm' (meters)

        Returns
        -------
            None
        """
        logger.info("Setting up hazard raster data")
        if not isinstance(hazard_fnames, list):
            hazard_fnames = [hazard_fnames]
        if risk and not return_periods:
            raise ValueError("Cannot perform risk analysis without return periods")
        if risk and len(return_periods) != len(hazard_fnames):
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
        ds = workflows.hazard_grid(
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
        if len(self.data.data_vars) > 1:
            self.model.config.set("hazard.settings.var_as_band", True)

        if risk:
            self.model.config.set("hazard.risk", risk)
            self.model.config.set("hazard.return_periods", return_periods)

        self.model.config.set("hazard.file", self._filename)
        self.model.config.set(
            "hazard.elevation_reference",
            "DEM" if hazard_type == "water_depth" else "datum",
        )
