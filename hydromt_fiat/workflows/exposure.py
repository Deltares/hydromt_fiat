import geopandas as gpd
import hydromt
from shapely.geometry import box


class Exposure:
    # TODO: Change name - look into hydroMT basemaps as name
    def setup_basemaps(
        self,
        region,
        **kwargs,
    ):
        """Define the model domain that is used to clip the raster layers.

        Adds model layer:

        * **region** geom: A geometry with the nomenclature 'region'.

        Parameters
        ----------
        region: dict
            Dictionary describing region of interest, e.g. {'bbox': [xmin, ymin, xmax, ymax]}. See :py:meth:`~hydromt.workflows.parse_region()` for all options.
        """

        kind, region = hydromt.workflows.parse_region(region, logger=self.logger)
        if kind == "bbox":
            geom = gpd.GeoDataFrame(geometry=[box(*region["bbox"])], crs=4326)
        elif kind == "grid":
            geom = region["grid"].raster.box
        elif kind == "geom":
            geom = region["geom"]
        else:
            raise ValueError(
                f"Unknown region kind {kind} for FIAT, expected one of ['bbox', 'grid', 'geom']."
            )

        # Set the model region geometry (to be accessed through the shortcut self.region).
        self.set_geoms(geom, "region")
