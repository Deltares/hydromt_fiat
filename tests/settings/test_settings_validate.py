from pathlib import Path

import pytest
from pydantic import ValidationError

from hydromt_fiat.settings import GeomSettings, GridSettings
from hydromt_fiat.settings.exposure import ExposureGeometry, ExposureGrid
from hydromt_fiat.settings.file import FileContext, InputFileModel, OutputFileModel
from hydromt_fiat.settings.hazard import Hazard
from hydromt_fiat.settings.variables import ExposureGridVariable, HazardVariable
from hydromt_fiat.settings.vulnerability import Vulnerability


def test_validate_exposure():
    # Setup the settings
    bs = GeomSettings(exposure=ExposureGeometry(file="foo.txt", vulnerability="a"))
    # Assert it's a list
    assert isinstance(bs.exposure, list)

    # Setup the settings
    bs = GeomSettings(exposure=[ExposureGeometry(file="foo.txt", vulnerability="a")])
    # Assert it's a list
    assert isinstance(bs.exposure, list)


def test_validate_exposure_geometry():
    # Assert the vulnerability is required
    with pytest.raises(ValidationError):
        ExposureGeometry(file="f.fgb")

    # Setup the exposure with a vulnerability
    exposure = ExposureGeometry(file="f.fgb", vulnerability="default")
    # Assert the vulnerability
    assert exposure.vulnerability == "default"


@pytest.mark.parametrize(
    "entry",
    [
        {"type": "default", "fn_curve": "a", "vulnerability": "v"},
        {"type": "default", "fn_curve": "a", "vulnerability": ["v", "w"]},
        {"type": "categorized", "values": ["x"]},
        {"type": "values", "vulnerability": "v"},
    ],
)
def test_validate_exposure_grid_variable(entry: dict):
    # Setup the variable
    var = ExposureGridVariable(name="e", **entry)

    # Assert the variable
    assert var.name == "e"


@pytest.mark.parametrize(
    "entry",
    [
        {},  # no type
        {"type": "combined", "vulnerability": "v"},
        {"type": "default", "fn_curve": "a"},  # no vulnerability
        {"type": "default", "vulnerability": "v"},  # no fn_curve
        {"type": "categorized", "vulnerability": "v"},
        {"type": "values"},  # no vulnerability
        {"type": "default", "fn_curve": "a", "vulnerability": "v", "values": ["x"]},
    ],
)
def test_validate_exposure_grid_variable_errors(entry: dict):
    # Assert the invalid combinations of fields
    with pytest.raises(ValidationError):
        ExposureGridVariable(name="e", **entry)


def test_validate_exposure_grid_errors():
    # Assert at least one variable is required
    with pytest.raises(ValidationError):
        ExposureGrid(file="e.nc", variables=[])


def test_validate_hazard_variable():
    # Setup the variable with a value (uniform)
    var = HazardVariable(name="d", type="duration", value=3.0)

    # Assert the value
    assert var.value == 3.0


def test_validate_hazard_errors():
    # Assert the type is required
    with pytest.raises(ValidationError):
        Hazard.model_validate({"file": "h.nc", "variables": [{"name": "d"}]})

    # Assert at least one variable is required
    with pytest.raises(ValidationError):
        Hazard(file="h.nc", variables=[])


def test_validate_vulnerability():
    # Setup the vulnerability
    v = Vulnerability.model_validate(
        {
            "file": "c.nc",
            "variables": [
                {
                    "name": "a",
                    "method": "flood.depth",
                    "types": {"depth_a": "water_depth"},
                }
            ],
        }
    )

    # Assert the types
    assert v.variables[0].types == {"depth_a": "water_depth"}


def test_validate_vulnerability_errors():
    base = {"name": "a", "method": "flood.depth", "types": {"depth_a": "water_depth"}}

    # Assert the method is required
    with pytest.raises(ValidationError):
        Vulnerability.model_validate(
            {"file": "c.nc", "variables": [{"name": "a", "types": {}}]}
        )

    # Assert at least one variable is required
    with pytest.raises(ValidationError):
        Vulnerability.model_validate({"file": "c.nc", "variables": []})

    with pytest.raises(ValidationError):
        Vulnerability.model_validate({"file": "c.nc"})

    # Assert a value is not allowed
    with pytest.raises(ValidationError):
        Vulnerability.model_validate(
            {"file": "c.nc", "variables": [{**base, "value": 1}]}
        )


def test_validate_risk():
    # Setup the hazard without a return period
    hazard = Hazard(
        file="h.nc", variables=[HazardVariable(name="a", type="water_depth")]
    )

    # Assert the return period is required for a risk calculation
    with pytest.raises(ValidationError, match="rp"):
        GridSettings(risk=True, hazard=hazard)

    # Setup the hazard with a return period
    hazard = Hazard(
        file="h.nc", variables=[HazardVariable(name="a", type="water_depth", rp=10)]
    )

    # Assert the settings are valid
    assert GridSettings(risk=True, hazard=hazard).risk
    # No hazard (incremental build) is valid
    assert GeomSettings(risk=True).risk


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
