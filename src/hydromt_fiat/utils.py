"""HydroMT-FIAT utility."""

__all__ = ["create_query"]


def create_query(
    **kwargs: dict,
):
    """Generate a query for a pandas DataFrame.

    Parameters
    ----------
    kwargs : dict
        Keyword arguments that are processed to a query. N.b. these are additive.
    """
    query = ""
    idx = 0
    for key, item in kwargs.items():
        if idx != 0:
            query += " and "
        idx += 1
        if isinstance(item, (list, tuple)):
            query += f"{key} in {str(item)}"
            continue
        if isinstance(item, str):
            item = f"'{item}'"
        query += f"{key} == {str(item)}"
    return query
