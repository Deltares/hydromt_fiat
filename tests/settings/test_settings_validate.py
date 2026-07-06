from pathlib import Path

import pytest

from hydromt_fiat.settings.exposure import Exposure, ExposureGeometry
from hydromt_fiat.settings.file import FileContext, InputFileModel, OutputFileModel
from hydromt_fiat.settings.model import Model
from hydromt_fiat.settings.output import Output, OutputGeometry


def test_validate_exposure():
    # Either provide as a single
    e = Exposure(geom=ExposureGeometry(file="foo.txt"))
    # Assert it's a list
    assert isinstance(e.geom, list)

    # Or provide as a list
    e = Exposure(geom=[ExposureGeometry(file="foo.txt")])
    # Assert it's a list
    assert isinstance(e.geom, list)


def test_validate_input_file():
    # Initialize
    f = InputFileModel(file="foo.txt")

    # Assert the state
    assert f.file == Path("foo.txt")


def test_validate_input_file_abs(tmp_path: Path):
    # Initialize
    f = InputFileModel(file=Path(tmp_path, "foo.txt"))

    # Assert the state
    assert f.file == Path(tmp_path, "foo.txt")


def test_validate_input_file_make_abs(tmp_path: Path):
    # Initialize
    f = InputFileModel.model_validate(
        {"file": "foo.txt"}, context=FileContext(config_dir=Path(tmp_path, "baz"))
    )

    # Assert the state
    assert f.file == Path(tmp_path, "baz", "foo.txt")


def test_validate_output_file():
    # Initialize
    f = OutputFileModel(file="foo.txt")

    # Assert the state
    assert f.file == Path("foo.txt")


def test_validate_output_file_abs(tmp_path: Path):
    # Initialize
    f = OutputFileModel(file=Path(tmp_path, "foo.txt"))

    # Assert the state
    assert f.file == Path(tmp_path, "foo.txt")


def test_validate_output_file_make_abs(tmp_path: Path):
    # Initialize
    f = OutputFileModel.model_validate(
        {"file": "foo.txt"}, context=FileContext(output_dir=Path(tmp_path, "baz"))
    )

    # Assert the state
    assert f.file == Path(tmp_path, "baz", "foo.txt")


def test_validate_model():
    # Initialize
    m = Model(type="geom")

    # Assert the type was set correctly
    assert m.type == "geom"


def test_validate_model_errors():
    # Set a nonsense model type
    with pytest.raises(
        ValueError,
        match="Model type should be either",
    ):
        _ = Model(type="foo")


def test_validate_output():
    # Either provide as a single
    e = Output(geom=OutputGeometry(file="foo.txt"))
    # Assert it's a list
    assert isinstance(e.geom, list)

    # Or provide as a list
    e = Output(geom=[OutputGeometry(file="foo.txt")])
    # Assert it's a list
    assert isinstance(e.geom, list)
