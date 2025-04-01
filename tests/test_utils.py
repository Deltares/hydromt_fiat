from hydromt_fiat.utils import create_query


def test_create_query_single_type():
    # Single values only
    query = create_query(
        var1="value",
        var2=2,
    )
    assert query == "var1 == 'value' and var2 == 2"


def test_create_query_combined_type():
    # Single value and an iterator (list)
    query = create_query(
        var1="value",
        var2=[1, 2, 3],
    )
    assert query == "var1 == 'value' and var2 in [1, 2, 3]"


def test_create_query_iter_type():
    # Lists only
    query = create_query(
        var1=["value1", "value2"],
        var2=[1, 2],
    )
    assert query == "var1 in ['value1', 'value2'] and var2 in [1, 2]"
