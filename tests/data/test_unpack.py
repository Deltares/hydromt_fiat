import tarfile
import zipfile
from pathlib import Path

import pytest

from hydromt_fiat.data.unpack import _is_archive, untar, unzip


def test__is_archive(
    tmp_json: Path,
    tmp_tarfile: Path,
    tmp_zipfile: Path,
):
    # Call the function
    f = _is_archive(tmp_tarfile)
    # Assert output
    assert f == (True, False)  # First True

    # Call the function
    f = _is_archive(tmp_zipfile)
    # Assert output
    assert f == (False, True)  # Second True

    # Call the function
    f = _is_archive(tmp_json)
    # Assert output
    assert f == (False, False)  # None True


def test_untar(tmp_path: Path, tmp_tarfile: Path):
    p = Path(tmp_path, "untar")
    # Call the function
    o = untar(tmp_tarfile, output_dir=p)
    # Assert the output
    assert o == p
    assert Path(p, "tmp.txt").is_file()
    assert Path(p, "tmp.json").is_file()


def test_untar_errors(tmp_json):
    # This is not a valid tarfile
    with pytest.raises(
        tarfile.TarError, match=f"'{tmp_json.as_posix()}' is not a tar file."
    ):
        untar(file=tmp_json)


def test_unzip(tmp_path: Path, tmp_zipfile: Path):
    p = Path(tmp_path, "unzip")
    # Call the function
    o = unzip(tmp_zipfile, output_dir=p)
    # Assert the output
    assert o == p
    assert Path(p, "tmp.txt").is_file()
    assert Path(p, "tmp.json").is_file()


def test_unzip_errors(tmp_json):
    # This is not a valid zipfile
    with pytest.raises(
        zipfile.error, match=f"'{tmp_json.as_posix()}' is not a zip file."
    ):
        unzip(file=tmp_json)
