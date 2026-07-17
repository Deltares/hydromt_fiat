from pathlib import Path

from hydromt_fiat.components.utils import (
    expand_path_wildcards,
)


def test_expand_path_wildcards(
    model_data_clipped_path: Path,
):
    # Call the function
    paths = expand_path_wildcards(
        root=model_data_clipped_path, filename="exposure/{name}.fgb"
    )
    # Assert the output
    assert len(paths) == 2
    assert paths[0].suffix == ".fgb"

    # To a directory with no data
    # Call the function
    paths = expand_path_wildcards(
        root=model_data_clipped_path, filename="foo/{name}.fgb"
    )
    # Assert the output
    assert len(paths) == 0


def test_expand_path_wildcards_none(
    model_data_clipped_path: Path,
):
    # Call the function
    out = expand_path_wildcards(root=model_data_clipped_path, filename=None)
    # Assert the output
    assert out is None
