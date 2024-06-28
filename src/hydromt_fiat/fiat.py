"""Main module."""

from logging import Logger, getLogger
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from hydromt import Model
from hydromt.io.readers import read_toml
from hydromt.model.components.config import ConfigComponent
from hydromt.model.components.grid import GridComponent
from hydromt.model.components.tables import TablesComponent
from hydromt.model.components.vector import VectorComponent

logger: Logger = getLogger(__name__)


class FIATModel(Model):
    """_summary_."""

    name: str = "FIAT_model"
    _MODEL_VERSION = "v1.0"

    def __init__(
        self,
        root: Optional[str] = None,
        *,
        components: Optional[Dict[str, Any]] = None,
        mode: str = "w",
        config_fn: Optional[str] = None,
        data_libs: Optional[Union[List, str]] = None,
        region_component: Optional[str] = None,
        **catalog_keys,
    ):
        components = {
            "grid": GridComponent,
            "vector": VectorComponent,
            "tables": TablesComponent,
        }
        super().__init__(
            root=root,
            components=components,
            mode=mode,
            data_libs=data_libs,
            region_component=region_component,
            **catalog_keys,
        )
        config = ConfigComponent(self, filename=config_fn)
        self.add_component(name="config", component=config)

    def setup_global_settings(
        self,
        crs: Optional[Union[str, int]] = None,
        gdal_cache: Optional[int] = None,
        keep_temp_files: Optional[bool] = None,
        thread: Optional[int] = None,
        chunk: Optional[List[int]] = None,
    ) -> None:
        """To setup Delft-FIAT global settings.

        Parameters
        ----------
        crs : Optional[str], optional
            _description_, by default None
        gdal_cache : Optional[int], optional
            _description_, by default None
        keep_temp_files : Optional[bool], optional
            _description_, by default None
        thread : Optional[int], optional
            _description_, by default None
        chunk : Optional[List[int]], optional
            _description_, by default None
        """
        if crs:
            self.config.set("global.crs", f"EPSG:{crs}")
        if gdal_cache:
            self.config.set("global.gdal_cache", gdal_cache)
        if keep_temp_files:
            self.config.set("global.keep_temp_files", keep_temp_files)
        if thread:
            self.config.set("global.thread", thread)
        if chunk:
            self.config.set("global.grid.chunk", chunk)

    def setup_output(
        self,
        output_dir: str = "output",
        output_csv_name: str = "output.csv",
        output_vector_name: Union[str, List[str]] = "spatial.gpkg",
    ) -> None:
        """To setup Delft-FIAT output folder and files.

        Parameters
        ----------
        output_dir : str, optional
            The name of the output directory, by default "output".
        output_csv_name : str, optional
            The name of the output csv file, by default "output.csv".
        output_vector_name : Union[str, List[str]], optional
            The name of the output vector file, by default "spatial.gpkg".
        """
        self.config.set("output_path", output_dir)
        self.config.set("output.csv.name", output_csv_name)

        if isinstance(output_vector_name, str):
            output_vector_name = [output_vector_name]
        for i, name in enumerate(output_vector_name):
            self.config.set(f"output.geom.name{str(i+1)}", name)

    def setup_vulnerability(
        self,
        vulnerability_fn: Union[str, Path],
        vulnerability_identifiers_and_linking_fn: Union[str, Path],
        unit: str,
        functions_mean: Union[str, List[str], None] = "default",
        functions_max: Union[str, List[str], None] = None,
        step_size: Optional[float] = None,
        continent: Optional[str] = None,
    ) -> None:
        """To setup the vulnerability curves from various possible inputs.

        Parameters
        ----------
        vulnerability_fn : Union[str, Path]
            The (relative) path or ID from the data catalog to the source of the
            vulnerability functions.
        vulnerability_identifiers_and_linking_fn : Union[str, Path]
            The (relative) path to the table that links the vulnerability functions and
            exposure categories.
        unit : str
            The unit of the vulnerability functions.
        functions_mean : Union[str, List[str], None], optional
            The name(s) of the vulnerability functions that should use the mean hazard
            value when using the area extraction method, by default "default" (this
            means that all vulnerability functions are using mean).
        functions_max : Union[str, List[str], None], optional
            The name(s) of the vulnerability functions that should use the maximum
            hazard value when using the area extraction method, by default None (this
            means that all vulnerability functions are using mean).
        """
        # Read the vulnerability data
        df_vulnerability = self.data_catalog.get_dataframe(vulnerability_fn)

        # Read the vulnerability linking table
        vf_ids_and_linking_df = self.data_catalog.get_dataframe(
            vulnerability_identifiers_and_linking_fn
        )

        tables = get_vulnerability_data(
            df_vulnerability,
            vf_ids_and_linking_df,
            continent=continent,
            unit=unit,
            functions_mean=functions_mean,
            functions_max=functions_max,
        )
        self.tables.set(tables, name="vulnerability")
        # Update config
        self.set_config("vulnerability.file", "vulnerability/vulnerability_curves.csv")
        self.set_config("vulnerability.unit", unit)

        if step_size:
            self.set_config("vulnerability.step_size", step_size)

    def setup_vulnerability_from_csv(self, csv_fn: Union[str, Path], unit: str) -> None:
        """Setup the vulnerability curves from one or multiple csv files.

        Parameters
        ----------
            csv_fn : str
                The full path to the folder which holds the single vulnerability curves.
            unit : str
                The unit of the water depth column for all vulnerability functions
                (e.g. meter).
        """
        table = get_vulnerability_data_from_csv(csv_fn, unit)
        self.tables.set(table, name="vulnerability")

    def setup_road_vulnerability(
        self,
        vertical_unit: str,
        threshold_value: float = 0.6,
        min_hazard_value: float = 0,
        max_hazard_value: float = 10,
        step_hazard_value: float = 1.0,
    ):
        table = get_road_vulnerability(
            vertical_unit=vertical_unit,
            threshold_value=threshold_value,
            min_hazard_value=min_hazard_value,
            max_hazard_value=max_hazard_value,
            step_hazard_value=step_hazard_value,
        )
        self.tables.set(table, name="road_vulnerability")

    def setup_exposure_buildings(
        self,
        asset_locations: Union[str, Path],
        occupancy_type: Union[str, Path],
        max_potential_damage: Union[str, Path],
        ground_floor_height: Union[int, float, str, Path, None],
        unit: str,
        occupancy_attr: Union[str, None] = None,
        occupancy_object_type: Union[str, List[str]] = None,
        extraction_method: str = "centroid",
        damage_types: List[str] = ["structure", "content"],
        damage_unit: str = "$",
        country: Union[str, None] = None,
        ground_elevation_file: Union[int, float, str, Path, None] = None,
        bf_conversion: bool = False,
        keep_unclassified: bool = True,
    ) -> None:
        """To setup building exposure (vector) data for Delft-FIAT.

        Parameters
        ----------
        asset_locations : Union[str, Path]
            The path to the vector data (points or polygons) that can be used for the
            asset locations.
        occupancy_type : Union[str, Path]
            The path to the data that can be used for the occupancy type.
        max_potential_damage : Union[str, Path]
            The path to the data that can be used for the maximum potential damage.
        ground_floor_height : Union[int, float, str, Path None]
            Either a number (int or float), to give all assets the same ground floor
            height or a path to the data that can be used to add the ground floor
            height to the assets.
        unit : str
            The unit of the ground_floor_height
        occupancy_attr : Union[str, None], optional
            The name of the field in the occupancy type data that contains the
            occupancy type, by default None (this means that the occupancy type data
            only contains one column with the occupancy type).
        extraction_method : str, optional
            The method that should be used to extract the hazard values from the
            hazard maps, by default "centroid".
        damage_types : Union[List[str], None], optional
            The damage types that should be used for the exposure data, by default
            ["structure", "content"]. The damage types are used to link the
            vulnerability functions to the exposure data.
        damage_unit: str, optional
            The currency/unit of the Damage data, default in USD $
        country : Union[str, None], optional
            The country that is used for the exposure data, by default None. This is
            only required when using the JRC vulnerability curves.
        bf_conversion: bool, optional
            If building footprints shall be converted into point data.
        keep_unclassified: bool, optional
            Whether building footprints without classification are removed or reclassified as "residential"
        """
        vector_data = get_exposure_buildings_data(
            asset_locations=asset_locations,
            occupancy_type=occupancy_type,
            max_potential_damage=max_potential_damage,
            ground_floor_height=ground_floor_height,
            unit=unit,
            occupancy_attr=occupancy_attr,
            occupancy_object_type=occupancy_object_type,
            extraction_method=extraction_method,
            damage_types=damage_types,
            damage_unit=damage_unit,
            country=country,
            ground_elevation_file=ground_elevation_file,
            bf_conversion=bf_conversion,
            keep_unclassified=keep_unclassified,
        )

        self.vector.set(vector_data, name="exposure_buildings")
        # Update the other config settings
        self.set_config("exposure.csv.file", "exposure/exposure.csv")
        self.set_config("exposure.geom.crs", self.exposure.crs)
        self.set_config("exposure.geom.unit", unit)
        self.set_config("exposure.damage_unit", damage_unit)

    @staticmethod
    def from_toml(path: Path) -> "FIATModel":
        """Construct a model with the components and other init arguments in the toml file located at `path`."""
        file_contents = read_toml(path)
        return FIATModel.from_dict(file_contents)
