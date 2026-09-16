"""Workflow utilities."""

import pandas as pd

from hydromt_fiat.utils import INDEX, VALUE, create_query


def process_table(
    table: pd.DataFrame | dict[str, float | int],
    column_name: str = VALUE,
    index_name: str = INDEX,
    **select,
) -> pd.DataFrame:
    """Process the exposure cost table data.

    Parameters
    ----------
    table : pd.DataFrame | dict[str, float  |  int]
        The tablular data, which can be provided as a DataFrame
        or a dictionary. The dictionary should have the object types as keys and the
        corresponding cost values as values.
    column_name : str, optional
        The name of the column when a dictionary is provided as input.
        By default 'value'.
    index_name : str, optional
        The name of the index column when a DataFrame is provided as input. It is also
        set as the name of index column (keys) when a dictionary is provided.
        By default 'index'.
    **select : dict, optional
        Keyword arguments to filter the table.

    Returns
    -------
    pd.DataFrame
        The processed table as a DataFrame.
    """
    # If the table is in dict format, convert it to a DataFrame
    if isinstance(table, dict):
        table = pd.DataFrame.from_dict(
            table, orient="index", columns=[column_name]
        ).reset_index(names=index_name)
        # Return the dataframe
        return table

    # Create a query from the kwargs
    if len(select) != 0:
        query = create_query(**select)
        table = table.query(query)
        # Check if the resulting DataFrame is empty after selection
        if len(table) == 0:
            raise ValueError(f"Select kwargs ({select}) resulted in no remaining data")
        # Transpose the cost table, rename index to object_type to easily merge
        # This is not the object type, but the specific max costs of that element
        table = table.T.reset_index(names=index_name)

    return table
