from typing import Any, Dict

from hydromt_fiat.api.data_types import DataCatalogEntry


def make_catalog_entry(name: str, **kwargs) -> Dict[str, Dict[str, Any]]:
    return {name: DataCatalogEntry.parse_obj(kwargs).dict(exclude_none=True)}
