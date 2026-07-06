from pathlib import Path

from hydromt_fiat.settings import Settings
from hydromt_fiat.settings.exposure import Exposure, ExposureGeometry
from hydromt_fiat.settings.file import FileContext, InputFileModel, OutputFileModel
from hydromt_fiat.settings.output import Output


def test_serialize_input_file():
    # Initialize
    f = InputFileModel(file="foo.txt")

    # Assert the state
    assert f.file == Path("foo.txt")

    # Assert the output
    assert f.model_dump()["file"] == "foo.txt"


def test_serialize_input_file_none(tmp_path: Path):
    # Initialize
    f = InputFileModel(file=Path(tmp_path, "foo.txt"))

    # Assert the state
    assert f.file == Path(tmp_path, "foo.txt")

    # Assert the output
    assert f.model_dump()["file"] == Path(tmp_path, "foo.txt").as_posix()


def test_serialize_input_file_relative(tmp_path: Path):
    # Initialize
    f = InputFileModel(file=Path(tmp_path, "foo.txt"))

    # Assert the state
    assert f.file == Path(tmp_path, "foo.txt")

    # Assert the output
    assert f.model_dump(context=FileContext(config_dir=tmp_path))["file"] == "foo.txt"


def test_serialize_output():
    # Initialize
    o = Output()
    # Assert the path
    assert o.path == Path("output")

    # When dumping it should become a string
    assert o.model_dump()["path"] == "output"


def test_serialize_output_file():
    # Initialize
    f = OutputFileModel(file="foo.txt")

    # Assert the state
    assert f.file == Path("foo.txt")

    # Assert the output
    assert f.model_dump()["file"] == "foo.txt"


def test_serialize_output_file_none(tmp_path: Path):
    # Initialize
    f = OutputFileModel(file=Path(tmp_path, "foo.txt"))

    # Assert the state
    assert f.file == Path(tmp_path, "foo.txt")

    # Assert the output
    assert f.model_dump()["file"] == Path(tmp_path, "foo.txt").as_posix()


def test_serialize_output_file_relative(tmp_path: Path):
    # Initialize
    f = OutputFileModel(file=Path(tmp_path, "foo.txt"))

    # Assert the state
    assert f.file == Path(tmp_path, "foo.txt")

    # Assert the output
    assert f.model_dump(context=FileContext(output_dir=tmp_path))["file"] == "foo.txt"


def test_serialize_settings():
    # Create settings
    s = Settings()

    # When dumping no exposure should be there
    assert "exposure" not in s.model_dump(exclude_none=True)

    # But settings a single geometry, should leave it in there
    s.exposure = Exposure(geom=ExposureGeometry(file="foo.txt"))

    # When dumping the exposure should be present
    assert "exposure" in s.model_dump(exclude_none=True)
