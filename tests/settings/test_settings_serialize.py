from pathlib import Path

from hydromt_fiat.settings.file import FileContext, InputFileModel, OutputFileModel


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
