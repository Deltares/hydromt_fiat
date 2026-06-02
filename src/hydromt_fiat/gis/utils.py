"""General gis utility."""

from pyproj.crs import CRS


def crs_representation(
    crs: CRS | None = None,
) -> str | None:
    """Create string representation of CRS object.

    Parameters
    ----------
    srs : CRS | None, optional
        The spatial reference system object, by default None.

    Returns
    -------
    str | None
        Either a string representing the srs or None.
    """
    if crs is None:
        return None
    auth = crs.to_authority()
    if auth is None:
        return crs.to_wkt()
    return ":".join(crs.to_authority())
