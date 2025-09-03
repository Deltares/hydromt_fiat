"""The custom exposure geometries component."""

import logging
from pathlib import Path
from typing import cast

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely.geometry as sg
from hydromt.model import Model
from hydromt.model.components import SpatialModelComponent
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components.utils import pathing_config, pathing_expand
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.utils import OBJECT_ID

__all__ = ["ExposureGeomsComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class ExposureGeomsComponent(SpatialModelComponent):
    """Custom exposure geometries component.

    Parameters
    ----------
    model : Model
        HydroMT model instance (FIATModel)
    filename : str
        The path to use for reading and writing of component data by default.
        by default "exposure/{name}.fgb".
    region_component : str, optional
        The name of the region component to use as reference for this component's
        region. If None, the region will be set to the union of all geometries in
        the data dictionary.
    region_filename : str, optional
        The path to use for writing the region data to a file. By default
        "region.geojson".
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: str = "exposure/{name}.fgb",
        region_component: str | None = None,
        region_filename: str = "region.geojson",
    ):
        self._data: dict[str : gpd.GeoDataFrame] = None
        self._filename: str = filename
        super().__init__(
            model,
            region_component=region_component,
            region_filename=region_filename,
        )

    ## Private methods
    def _initialize(self, skip_read=False) -> None:
        """Initialize exposure geoms data structure (dict)."""
        if self._data is None:
            self._data = dict()
            if self.root.is_reading_mode() and not skip_read:
                self.read()

    ## Properties
    @property
    def _region_data(self) -> gpd.GeoDataFrame | None:
        # Use the total bounds of all geometries as region
        if len(self.data) == 0:
            return None
        bounds = np.column_stack([geom.total_bounds for geom in self.data.values()])
        total_bounds = (
            bounds[0, :].min(),
            bounds[1, :].min(),
            bounds[2, :].max(),
            bounds[3, :].max(),
        )
        region = gpd.GeoDataFrame(geometry=[sg.box(*total_bounds)], crs=self.model.crs)

        return region

    @property
    def data(self) -> dict[str, gpd.GeoDataFrame | gpd.GeoSeries]:
        """Model geometries.

        Return dict of geopandas.GeoDataFrame or geopandas.GeoSeries
        """
        if self._data is None:
            self._initialize()
        assert self._data is not None
        return self._data

    ## I/O methods
    @hydromt_step
    def read(
        self,
        filename: str | None = None,
        **kwargs,
    ) -> None:
        r"""Read exposure geometry files.

        Key-word arguments are passed to :py:func:`geopandas.read_file`

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root. should contain a {name} placeholder
            which will be used to determine the names/keys of the geometries.
            if None, the path that was provided at init will be used.
        kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.read_file` function.
        """
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort the filenames
        # Hierarchy: 1) signature, 2) settings file, 3) default
        out = (
            pathing_expand(self.root.path, filename=filename)
            or pathing_config(
                self.model.config.get("exposure.geom.file", abs_path=True)
            )
            or pathing_expand(self.root.path, filename=self._filename)
        )
        # Loop through the found files
        logger.info("Reading the exposure vector data..")
        for p, n in zip(*out):
            logger.info(f"Reading {n} at {p.as_posix()}")
            # Get the data
            geom = cast(gpd.GeoDataFrame, gpd.read_file(p, **kwargs))
            # Check for data in csv file, this has to be merged
            # TODO this should be solved better with help of the config file
            csv_path = p.with_suffix(".csv")
            if csv_path.is_file():
                csv_data = pd.read_csv(csv_path)
                geom = geom.merge(csv_data, on=OBJECT_ID)
            # Set the data
            self.set(geom=geom, name=n)

    @hydromt_step
    def write(
        self,
        filename: str | None = None,
        csv: bool = False,
        **kwargs,
    ):
        """Write exposure geometries to a vector file.

        Key-word arguments are passed to :py:meth:`geopandas.GeoDataFrame.to_file`

        Parameters
        ----------
        filename : str, optional
            Filename relative to model root. should contain a {name} placeholder
            which will be used to determine the names/keys of the geometries.
            if None, the path that was provided at init will be used.
        csv : bool, optional
            Whether to split the data into a pure vector file and a csv containing
            all the field information of the geometries.
        kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.to_file` function.
        """
        self.root._assert_write_mode()

        # If no data to write, return
        if len(self.data) == 0:
            logger.info("No geoms data found, skip writing.")
            return

        # Sort the filename
        # Hierarchy: 1) Signature, 2) default
        filename = filename or self._filename

        # The entries for the config
        cfg = []

        # Loop through the datasets
        logger.info("Writing the exposure vector data..")
        for name, gdf in self.data.items():
            if len(gdf) == 0:
                logger.warning(f"{name} is empty. Skipping...")
                continue

            # Abuse the fact that a dictionary is mutable and passed by ref
            entry = {}
            cfg.append(entry)

            # Create the outgoing file path
            write_path = Path(
                self.root.path,
                filename.format(name=name),
            )

            logger.info(f"Writing file to {write_path.as_posix()}")

            write_dir = write_path.parent
            if not write_dir.is_dir():
                write_dir.mkdir(parents=True, exist_ok=True)

            entry["file"] = write_path
            entry["srs"] = ":".join(gdf.crs.to_authority())
            entry["csv"] = csv

            if not csv:
                # Write the entire thing to vector file
                gdf.to_file(write_path, **kwargs)
                continue

            # Split into the vector only file
            geom = gdf.loc[:, [OBJECT_ID, "geometry"]]
            geom.to_file(write_path, **kwargs)
            geom = None

            # And the data file
            cols = gdf.columns.values.tolist()
            cols.remove("geometry")
            data = gdf.loc[:, cols]
            data.to_csv(write_path.with_suffix(".csv"), index=False)
            data = None

        # Set the config entries
        self.model.config.set("exposure.geom", cfg)

    ## Set(up) methods
    def set(
        self,
        geom: gpd.GeoDataFrame,
        name: str,
    ):
        """Add data to the geom component.

        Arguments
        ---------
        geom : gpd.GeoDataFrame
            New geometry data to add
        name : str
            Geometry name.
        """
        self._initialize()
        assert self._data is not None
        if name in self._data and id(self._data.get(name)) != id(geom):
            logger.warning(f"Replacing geom: {name}")

        if "fid" in geom.columns:
            logger.warning(
                f"'fid' column encountered in {name}, \
column will be removed"
            )
            geom.drop("fid", axis=1, inplace=True)

        # Verify if a geom is set to model crs and if not sets geom to model crs
        try:
            model_crs = self.model.crs
            if model_crs and model_crs != geom.crs:
                geom.to_crs(model_crs.to_epsg(), inplace=True)
        except AttributeError:
            pass
        self._data[name] = geom

    ## Setup methods
    @hydromt_step
    def setup(
        self,
        exposure_fname: Path | str,
        exposure_type_column: str,
        *,
        exposure_link_fname: Path | str | None = None,
        exposure_type_fill: str | None = None,
    ) -> None:
        """Set up the exposure from a data source.

        Will link with the vulnerability data to set a curve for each
        exposure type.

        Warning
        -------
        Run `setup_vulnerability` beforehand (see vulnerability component).

        Parameters
        ----------
        exposure_fname : Path | str
            The name of/ path to the raw exposure dataset.
        exposure_type_column : str
            The name of column in the raw dataset that specifies the object type,
            e.g. the occupancy type.
        exposure_link_fname : Path | str | None, optional
            The name of/ path to the dataset containing the mapping of the exposure
            types to the vulnerability data, by default None
        exposure_type_fill : str, optional
            Value to which missing entries in the exposure type column will be mapped
            to, if provided. By default None
        """
        logger.info("Setting up exposure geometries")
        # Check for region
        if self.model.region is None:
            # TODO Replace with custom error class
            raise MissingRegionError(
                "Region is None -> \
use 'setup_region' before this method"
            )
        # Check for vulnerability
        vulnerability = self.model.vulnerability.data
        if any([item.empty for item in vulnerability]):
            # TODO Replace with custom error class
            raise RuntimeError("Use `setup_vulnerability` before this method")

        # Guarantee typing
        exposure_fname = Path(exposure_fname)
        name = exposure_fname.stem

        # Get ze data
        exposure_data = self.model.data_catalog.get_geodataframe(
            data_like=exposure_fname,
            geom=self.model.region,
        )
        exposure_linking = None
        if exposure_link_fname is not None:
            exposure_linking = self.model.data_catalog.get_dataframe(
                data_like=exposure_link_fname,
            )

        # Call the workflows function(s) to manipulate the data
        exposure_vector = workflows.exposure_setup(
            exposure_data=exposure_data,
            exposure_type_column=exposure_type_column,
            exposure_linking=exposure_linking,
            exposure_type_fill=exposure_type_fill,
        )
        exposure_vector = workflows.exposure_vulnerability_link(
            exposure_data=exposure_vector,
            vulnerability=vulnerability.identifiers,
        )

        # Set the data in the component
        self.set(exposure_vector, name=name)

    @hydromt_step
    def setup_max_damage(
        self,
        exposure_name: str,
        exposure_type: str,
        exposure_cost_table_fname: Path | str,
        exposure_cost_link_fname: Path | str | None = None,
        **select: dict,
    ) -> None:
        """Set up the maximum potential damage per object in an existing dataset.

        Warning
        -------
        Run `setup_vulnerability` beforehand (see vulnerability component).

        Parameters
        ----------
        exposure_name : str
            The name of the existing dataset.
        exposure_type : str
            Type of exposure corresponding with the vulnerability data, e.g. 'damage'.
        exposure_cost_table_fname : Path | str
            The name of/ path to the mapping of the costs per subtype of the
            exposure type, e.g. 'residential_structure' or 'residential_content'.
        exposure_cost_link_fname : Path | str, optional
            A linking table to like the present object type with the identifiers
            defined in the cost table. If None, it is assumed the present object type
            matches the identifiers in the cost table. By default None.
        **select : dict
            Keyword arguments used to select data from the exposure cost table.
            E.g. a column is present named 'country' and the wanted values are in the
            row with 'UK', provided country='UK' as keyword argument.
        """
        logger.info(f"Setting up maximum potential damage for {exposure_name}")
        # Some checks on the input
        if exposure_name not in self.data:
            raise RuntimeError(
                f"Run `setup_exposure_geoms` before this methods \
with '{exposure_name}' as input or chose from already present geometries: \
{list(self.data.keys())}"
            )
        # Get the exposure costs table from the data catalog
        exposure_cost_table = self.model.data_catalog.get_dataframe(
            exposure_cost_table_fname,
        )
        # Get the exposure cost link is not None
        exposure_cost_link = None
        if exposure_cost_link_fname is not None:
            exposure_cost_link = self.model.data_catalog.get_dataframe(
                exposure_cost_link_fname,
            )

        # Call the workflows function to add the max damage
        exposure_vector = workflows.max_monetary_damage(
            self.data[exposure_name],
            exposure_cost_table=exposure_cost_table,
            exposure_type=exposure_type,
            vulnerability=self.model.vulnerability.data.identifiers,
            exposure_cost_link=exposure_cost_link,
            **select,
        )

        # Set the data back, its a bit symbolic as the dataframe is mutable...
        self.set(exposure_vector, exposure_name)

    @hydromt_step
    def update_column(
        self,
        exposure_name: str,
        columns: list[str],
        values: int | float | list | np.ndarray,
    ) -> None:
        """Update an existing dataset by adding columns with values.

        Parameters
        ----------
        exposure_name : str
            The name of the existing dataset.
        columns : list[str]
            A list of the names of the columns.
        values : int | float | list | np.ndarray
            The correspoding values of the columns. Either a single value set for
            all columns, a list of values corresponding to the number of columns or
            a 2d array.
        """
        logger.info(f"Updating exposure data with {columns} columns")
        # Some checks on the input
        if exposure_name not in self.data:
            raise RuntimeError(
                f"Run `setup_exposure_geoms` before this methods \
with '{exposure_name}' as input or chose from already present geometries: \
{list(self.data.keys())}"
            )

        # Call the workflow function
        exposure_vector = workflows.exposure_add_columns(
            self.data[exposure_name], columns=columns, values=values
        )

        # Symbolically set back the data
        self.set(exposure_vector, name=exposure_name)
