"""The exposure geometries component."""

import logging
from pathlib import Path
from typing import Any, cast

import geopandas as gpd
import numpy as np
import numpy.typing as npt
import pandas as pd
from hydromt.model import Model
from hydromt.model.steps import hydromt_step

from hydromt_fiat import workflows
from hydromt_fiat.components.geom import GeomsComponent
from hydromt_fiat.components.utils import pathing_config, pathing_expand
from hydromt_fiat.components.vulnerability import EXPOSURE_GEOM_COL
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.gis.utils import crs_representation
from hydromt_fiat.utils import (
    EXPOSURE,
    EXPOSURE_GEOM,
    EXPOSURE_GEOM_FILE,
    FILE,
    GEOM,
    MODEL_TYPE,
    OBJECT_ID,
    SETTINGS,
    SRS,
)

__all__ = ["ExposureGeomsComponent"]

logger = logging.getLogger(f"hydromt.{__name__}")


class ExposureGeomsComponent(GeomsComponent):
    """Exposure geometries component.

    Parameters
    ----------
    model : Model
        HydroMT model instance (FIATModel).
    filename : Path | str, optional
        The path to use for reading and writing of component data by default.
        By default "exposure/{name}.fgb".
    region_component : str, optional
        The name of the region component to use as reference for this component's
        region. If None, the region will be set to the union of all geometries in
        the data dictionary. By default None.
    """

    def __init__(
        self,
        model: Model,
        *,
        filename: Path | str = f"{EXPOSURE}/{{name}}.fgb",
        region_component: str | None = None,
    ):
        self._filename: Path | str = filename
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
        r"""Read exposure geometry files.

        Key-word arguments are passed to :py:func:`geopandas.read_file`.

        Parameters
        ----------
        filename : Path | str, optional
            Filename relative to model root. should contain a {name} placeholder
            which will be used to determine the names/keys of the geometries.
            If None, the value(s) is/ are either taken from the model configurations or
            the `_filename` attribute, by default None.
        **kwargs : dict
            Additional keyword arguments that are passed to the
            `geopandas.read_file` function.
        """
        self.root._assert_read_mode()
        self._initialize(skip_read=True)

        # Sort the filenames
        # Hierarchy: 1) signature, 2) settings file, 3) default
        files = (
            pathing_expand(self.root.path, filename=filename)
            or pathing_config(self.model.config.get(EXPOSURE_GEOM_FILE, abs_path=True))
            or pathing_expand(self.root.path, filename=self._filename)
        )
        assert files is not None  # Yh..
        # Loop through the found files
        logger.info("Reading the exposure vector data..")
        for read_path, name in zip(*files):
            if not read_path.is_file():
                continue
            logger.info(f"Reading the {name} geometry file at {read_path.as_posix()}")
            # Get the data
            data = cast(gpd.GeoDataFrame, gpd.read_file(read_path, **kwargs))
            # Check for data in csv file, this has to be merged
            # TODO this should be solved better with help of the config file
            csv_path = read_path.with_suffix(".csv")
            if csv_path.is_file():
                csv_data = pd.read_csv(csv_path)
                data = data.merge(csv_data, on=OBJECT_ID)
            # Set the data
            self.set(data=data, name=name)

    @hydromt_step
    def write(
        self,
        filename: Path | str | None = None,
        **kwargs,
    ) -> None:
        """Write exposure geometries to a vector file.

        Key-word arguments are passed to :py:meth:`geopandas.GeoDataFrame.to_file`.

        Parameters
        ----------
        filename : Path | str, optional
            Filename relative to model root. Should contain a {name} placeholder
            which will be used to determine the names/keys of the geometries.
            If None, the value(s) is/ are either taken from the model configurations or
            the `_filename` attribute, by default None.
        **kwargs : dict
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
        filename = Path(filename).as_posix()

        # The entries for the config
        cfg = []

        # Loop through the datasets
        logger.info("Writing the exposure vector data..")
        for name, gdf in self.data.items():
            if len(gdf) == 0:
                logger.warning(f"{name} is empty. Skipping...")
                continue

            # Abuse the fact that a dictionary is mutable and passed by ref
            entry: dict[str, Any] = {}
            cfg.append(entry)
            # Create the outgoing file path
            write_path = Path(
                self.root.path,
                filename.format(name=name),
            )
            # Ensure the directory
            write_dir = write_path.parent
            if not write_dir.is_dir():
                write_dir.mkdir(parents=True, exist_ok=True)

            entry[FILE] = write_path
            # Due to header overloading, this is not solved properly in
            # the config component
            if gdf.crs is not None:
                entry[SETTINGS] = {SRS: crs_representation(gdf.crs)}
            logger.info(
                f"Writing the '{name}' geometry data to {write_path.as_posix()}",
            )
            # Write the entire thing to vector file
            gdf.to_file(write_path, **kwargs)

        # Set the config entries
        self.model.config.set(EXPOSURE_GEOM, cfg)

    ## Setup methods
    @hydromt_step
    def setup(
        self,
        exposure_fname: Path | str,
        exposure_type_column: str,
        *,
        vulnerability_link_fname: Path | str | None = None,
        exposure_link_fname: Path | str | None = None,
        exposure_type_fill: str | None = None,
        predicate: str = "contains",
    ) -> None:
        """Set up the exposure from a data source.

        Loads the raw exposure dataset, applies the optional OSM-tag → typology
        mapping, and stores the result. If ``vulnerability_link_fname`` is
        provided, immediately links the exposure to the shared vulnerability
        curves (curves must already exist). Otherwise the exposure is stored
        unlinked and you must call :py:meth:`setup_link_vulnerability` later.

        Parameters
        ----------
        exposure_fname : Path | str
            The name of/ path to the raw exposure dataset.
        exposure_type_column : str
            The name of column in the raw dataset that specifies the object type,
            e.g. the occupancy type.
        vulnerability_link_fname : Path | str | None, optional
            Data catalog entry or path to a linking CSV describing how this
            exposure's typologies map to curves (and optionally subtypes). If
            provided, the link is applied immediately and the curves library
            must already be populated (run :py:meth:`VulnerabilityComponent.setup`
            first). If omitted, defer the linking to a later call to
            :py:meth:`setup_link_vulnerability`. By default None.
        exposure_link_fname : Path | str | None, optional
            Optional dataset containing the mapping of the exposure types to the
            vulnerability data, by default None.
        exposure_type_fill : str, optional
            Value to which missing entries in the exposure type column will be mapped
            to, if provided. By default None.
        predicate : str, optional
            Method on how to select the data that falls within the region geometry.
            For more information see `geopandas.sjoin`. By default 'contains'.
        """
        logger.info("Setting up exposure geometries")
        # Check for region
        if self.model.region is None:
            # TODO Replace with custom error class
            raise MissingRegionError(
                "Region is None -> \
use 'setup_region' before this method"
            )

        # Get the name based on the stem of a path
        name = Path(exposure_fname).stem

        # Get ze data
        exposure_data = self.model.data_catalog.get_geodataframe(
            data_like=exposure_fname,
            geom=self.model.region,
            predicate=predicate,
        )
        exposure_linking = None
        if exposure_link_fname is not None:
            exposure_linking = self.model.data_catalog.get_dataframe(
                data_like=exposure_link_fname,
            )

        # Call the workflows function(s) to manipulate the data
        exposure_vector = workflows.exposure_geoms_setup(
            exposure_data=exposure_data,
            exposure_type_column=exposure_type_column,
            exposure_linking=exposure_linking,
            exposure_type_fill=exposure_type_fill,
        )

        # Store the prepared exposure data first so setup_link_vulnerability
        # can operate on it if the user supplied a link.
        self.set(exposure_vector, name=name)

        # Optionally link to the vulnerability curves in the same call
        if vulnerability_link_fname is not None:
            self.setup_link_vulnerability(
                exposure_name=name,
                vulnerability_link_fname=vulnerability_link_fname,
            )

        # Update the config
        logger.info("Setting the model type to 'geom'")
        self.model.config.set(MODEL_TYPE, GEOM)

    @hydromt_step
    def setup_link_vulnerability(
        self,
        exposure_name: str,
        vulnerability_link_fname: Path | str,
    ) -> None:
        """Link an existing exposure dataset to the vulnerability curves.

        Validates ``vulnerability_link_fname`` against the curves library,
        populates the ``fn_*`` columns on the exposure rows, and appends the
        per-exposure link rows to ``model.vulnerability.data.identifiers``
        (tagged with the exposure dataset name).

        Use this when you set up the exposure with ``vulnerability_link_fname=None``
        and want to defer the linking, or to re-link a freshly re-setup exposure.

        Warning
        -------
        Run :py:meth:`VulnerabilityComponent.setup` and :py:meth:`setup` for
        ``exposure_name`` beforehand.

        Parameters
        ----------
        exposure_name : str
            The name of an existing exposure dataset already loaded by
            :py:meth:`setup`.
        vulnerability_link_fname : Path | str
            Data catalog entry or path to a linking CSV describing how this
            exposure's typologies map to curves (and optionally subtypes).
        """
        logger.info(f"Linking '{exposure_name}' to vulnerability curves")
        self._assert_entry(exposure_name)

        if self.model.vulnerability.data.curves.empty:
            raise RuntimeError(
                "No vulnerability curves found — run `vulnerability.setup` "
                "before this method."
            )

        # Refuse to silently re-link a dataset that's already linked
        identifiers = self.model.vulnerability.data.identifiers
        if (
            not identifiers.empty
            and EXPOSURE_GEOM_COL in identifiers.columns
            and exposure_name in identifiers[EXPOSURE_GEOM_COL].values
        ):
            raise RuntimeError(
                f"'{exposure_name}' is already linked. Re-run `setup` to start "
                "fresh, or unlink first."
            )

        # Resolve and validate the per-exposure vulnerability link
        link_raw = self.model.data_catalog.get_dataframe(
            data_like=vulnerability_link_fname,
        )
        link = workflows.build_vulnerability_link(
            link_raw,
            curves=self.model.vulnerability.data.curves,
        )

        # Join the exposure rows to the scoped link
        exposure_vector = workflows.exposure_geoms_link_vulnerability(
            exposure_data=self.data[exposure_name],
            vulnerability=link,
        )

        # Append the link rows to the shared identifiers table and update the geom
        self.model.vulnerability.append_identifiers(name=exposure_name, link=link)
        self.set(exposure_vector, name=exposure_name)

    @hydromt_step
    def setup_max_damage(
        self,
        exposure_name: str,
        exposure_type: str,
        exposure_cost_table_fname: Path | str,
        exposure_cost_link_fname: Path | str | None = None,
        **select,
    ) -> None:
        """Set up the maximum potential damage per object in an existing dataset.

        Looks up the per-exposure vulnerability link from
        ``model.vulnerability.data.identifiers`` (filtered by exposure dataset
        name) to discover the relevant subtypes and to drive the default
        ``exposure_cost_link``.

        Warning
        -------
        Run :py:meth:`setup` for ``exposure_name`` beforehand.

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
        self._assert_entry(exposure_name)
        identifiers = self.model.vulnerability.data.identifiers
        if identifiers.empty or EXPOSURE_GEOM_COL not in identifiers.columns:
            raise KeyError(
                f"No vulnerability identifiers found for '{exposure_name}'. "
                "Did you run `setup` for this exposure dataset first?"
            )
        link = identifiers[identifiers[EXPOSURE_GEOM_COL] == exposure_name]
        if link.empty:
            available = sorted(identifiers[EXPOSURE_GEOM_COL].unique())
            raise KeyError(
                f"No vulnerability identifiers found for '{exposure_name}'. "
                f"Available: {available}. Did you run `setup` for this exposure "
                "dataset first?"
            )
        link = link.drop(columns=[EXPOSURE_GEOM_COL]).reset_index(drop=True)

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
            vulnerability=link,
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
        values: int
        | float
        | str
        | list[int | float | str]
        | npt.NDArray[np.int64 | np.float64 | np.str_],
    ) -> None:
        """Update an existing dataset by adding columns with values.

        Parameters
        ----------
        exposure_name : str
            The name of the existing dataset.
        columns : list[str]
            A list of the names of the columns.
        values : int | float | str | list | np.ndarray
            The correspoding values of the columns. Either a single value set for
            all columns, a list of values corresponding to the number of columns or
            a 2d array.
        """
        logger.info(f"Updating exposure data with {columns} columns")
        # Some checks on the input
        self._assert_entry(exposure_name)

        # Call the workflow function
        exposure_vector = workflows.exposure_geoms_add_columns(
            self.data[exposure_name], columns=columns, values=values
        )

        # Symbolically set back the data
        self.set(exposure_vector, name=exposure_name)
