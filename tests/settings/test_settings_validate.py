from pathlib import Path

from hydromt_fiat.settings import GeomSettings
from hydromt_fiat.settings.exposure import ExposureGeometry
from hydromt_fiat.settings.file import FileContext, InputFileModel, OutputFileModel


def test_validate_exposure():
    # Setup the settings
    bs = GeomSettings(exposure=ExposureGeometry(file="foo.txt"))
    # Assert it's a list
    assert isinstance(bs.exposure, list)

    # Setup the settings
    bs = GeomSettings(exposure=[ExposureGeometry(file="foo.txt")])
    # Assert it's a list
    assert isinstance(bs.exposure, list)


def test_validate_output():
    # Setup the settings
    bs = GeomSettings(output=OutputFileModel(file="foo.txt"))
    # Assert it's a list
    assert isinstance(bs.output, list)

    # Setup the settings
    bs = GeomSettings(output=[OutputFileModel(file="foo.txt")])
    # Assert it's a list
    assert isinstance(bs.output, list)


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
