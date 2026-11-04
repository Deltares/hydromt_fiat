from pathlib import Path

from hydromt_fiat.settings import BaseSettings, GeomSettings, GridSettings
from hydromt_fiat.settings.exposure import ExposureGeometry, ExposureGrid
from hydromt_fiat.settings.file import FileContext, InputFileModel, OutputFileModel
from hydromt_fiat.settings.hazard import Hazard
from hydromt_fiat.settings.variables import (
    ExposureGridVariable,
    HazardVariable,
    VulnerabilityVariable,
)
from hydromt_fiat.settings.vulnerability import Vulnerability


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
    bs = BaseSettings()
    # Assert the path
    assert bs.output_dir == Path("output")

    # When dumping it should become a string
    assert bs.model_dump()["output_dir"] == "output"


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
    s = GeomSettings(type="geom")

    # When dumping no exposure should be there
    assert "exposure" not in s.model_dump(exclude_none=True)

    # But settings a single geometry, should leave it in there
    s.exposure = ExposureGeometry(file="foo.txt", vulnerability="default")

    # When dumping the exposure should be present
    assert "exposure" in s.model_dump(exclude_none=True)


def test_serialize_settings_variables():
    # Create settings with variables
    s = GridSettings(
        vulnerability=Vulnerability(
            file="v.nc",
            variables=[
                VulnerabilityVariable(
                    name="a", method="flood.depth", types={"depth_a": "water_depth"}
                )
            ],
        ),
        hazard=Hazard(
            file="h.nc", variables=[HazardVariable(name="d", type="water_depth")]
        ),
        exposure=ExposureGrid(
            file="e.nc",
            variables=[
                ExposureGridVariable(
                    name="e", type="default", fn_curve="s1", vulnerability=["a", "b"]
                )
            ],
        ),
    )

    # Dump to a dictionary
    data = s.to_dict()

    # Assert the variables are present
    assert data["exposure"]["variables"][0] == {
        "name": "e",
        "type": "default",
        "vulnerability": ["a", "b"],
        "fn_curve": "s1",
    }
    assert data["vulnerability"]["variables"][0]["types"] == {"depth_a": "water_depth"}
    # Assert there is no method on the global level
    assert "method" not in data
