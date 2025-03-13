"""Main module."""

from pathlib import Path
from typing import Any, Dict, List, Union

from hydromt import Model


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

    def setup_hazard(
        self,
        hazard_fname: Path | str,
        risk: bool = False,
        return_period: List[int | float] | None = None,
    ):
        """_summary_."""
        hazard = self.data_catalog.get_rasterdataset(hazard_fname)
        return hazard
