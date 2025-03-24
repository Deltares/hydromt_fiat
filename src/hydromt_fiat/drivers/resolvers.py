"""Resolve uri argument for OSM data catalog sources."""

from pathlib import Path

from hydromt.data_catalog.uri_resolvers import URIResolver

__all__ = ["OSMResolver"]

__hydromt_eps__ = ["OSMResolver"]


class OSMResolver(URIResolver):
    """Resolve uri argument for OSM data catalog sources."""

    name = "osm_resolver"

    def resolve(self, uri, **kwargs) -> list[str]:
        """Resolve OSM uri argument."""
        uri = Path(uri).stem
        return [uri]
