import logging
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import geopandas as gpd
import numpy as np
import pytest
import xarray as xr
from hydromt.model import ModelRoot
from hydromt.model.mode import ModelMode
from pytest_mock import MockerFixture

from hydromt_fiat import FIATModel
from hydromt_fiat.components import ExposureGridComponent
from hydromt_fiat.errors import MissingRegionError
from hydromt_fiat.settings.exposure import ExposureGridVariable
from hydromt_fiat.utils import (
    CATEGORIZED,
    DEFAULT,
    EXPOSURE,
    FN__CURVE,
    GRID,
    INDEX,
    VALUE,
    VALUES,
    VULNERABILITY,
)
from hydromt_fiat.workflows import infer_exposure_grid_attrs


def test_exposure_grid_component_empty(
    mock_model: MagicMock,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model("grid"))

    # Assert some basics
    assert component._filename == f"{EXPOSURE}/spatial.nc"
    assert len(component.data) == 0
    assert isinstance(component.data, xr.Dataset)


def test_exposure_grid_component_read(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    # Setup the model
    model = mock_model_config("grid")
    type(model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    model.config.read("settings_grid.toml")
    # Setup the component
    component = ExposureGridComponent(model=model)

    # Read the data by calling the data property
    component.data

    # No config so it wont read anything
    assert len(component.data.data_vars) == 7
    assert "industrial_content" in component.data.data_vars
    # Assert the attributes, which are taken from the settings
    assert set(component.data_attrs) == set(component.data.data_vars)
    assert component.data_attrs["industrial_content"].type == DEFAULT
    assert component.data_attrs["industrial_content"].fn_curve == "in2"
    assert component.data_attrs["buildings"].type == CATEGORIZED
    assert component.data_attrs["buildings_structure"].type == VALUES


def test_exposure_grid_component_read_sig(
    mock_model_config: MagicMock,
    model_data_clipped_path: Path,
):
    # Setup the model
    model = mock_model_config("grid")
    type(model).root = PropertyMock(
        side_effect=lambda: ModelRoot(model_data_clipped_path, mode="r"),
    )
    # Setup the component
    component = ExposureGridComponent(model=model)

    # Read the data using the signature of the read method
    component.read(f"{EXPOSURE}/spatial.nc")

    # No config so it wont read anything
    assert len(component.data.data_vars) == 7
    assert "industrial_content" in component.data.data_vars
    # Assert the attributes, which are inferred as there are no settings present
    assert set(component.data_attrs) == set(component.data.data_vars)
    assert component.data_attrs["industrial_content"].type == DEFAULT


def test_exposure_grid_component_read_nothing(
    mocker: MockerFixture,
    mock_model_config: MagicMock,
):
    # Setup the model
    model = mock_model_config("grid")
    mocker.patch.object(
        type(model.root),
        "mode",
        new_callable=PropertyMock,
        return_value=ModelMode("r"),
    )
    # Setup the component
    component = ExposureGridComponent(model=model)
    # Assert current state
    assert len(component.data) == 0

    # Read the data (nothing)
    component.read()
    # Assert still no data
    assert len(component.data) == 0


def test_exposure_grid_component_write(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config("grid"))

    # Set data like a dummy
    component._data = exposure_grid_clipped
    component._data_attrs = {}
    for name, attrs in infer_exposure_grid_attrs(exposure_grid_clipped).items():
        component.set_attrs(name, attrs)

    # Write the data
    component.write()

    # Assert the output
    assert Path(tmp_path, EXPOSURE, "spatial.nc").is_file()
    # Assert the config
    assert component.model.config.data.exposure.file == Path(
        tmp_path,
        EXPOSURE,
        "spatial.nc",
    )
    variables = component.model.config.data.exposure.variables
    assert len(variables) == len(exposure_grid_clipped.data_vars)
    assert all(isinstance(item, ExposureGridVariable) for item in variables)


def test_exposure_grid_component_write_none(
    caplog: pytest.LogCaptureFixture,
    mock_model_config: MagicMock,
):
    caplog.set_level(logging.INFO)
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config("grid"))

    # Call write
    component.write()

    # Assert logging message
    assert "No exposure grid data found, skip writing" in caplog.text


def test_exposure_grid_component_write_sig(
    tmp_path: Path,
    mock_model_config: MagicMock,
    exposure_grid_clipped: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config("grid"))

    # Set data like a dummy
    component._data = exposure_grid_clipped
    component._data_attrs = {}
    for name, attrs in infer_exposure_grid_attrs(exposure_grid_clipped).items():
        component.set_attrs(name, attrs)

    # Write the data
    component.write("baz.nc")

    # Assert the output
    assert Path(tmp_path, "baz.nc").is_file()
    # Assert the config file
    assert component.model.config.data.exposure.file == Path(
        tmp_path,
        "baz.nc",
    )


def test_exposure_grid_component_write_errors(
    mock_model_config: MagicMock,
    hazard: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=mock_model_config("grid"))
    # Set data like a dummpy, it's hazard data, so with the wrong attributes
    component._data = hazard

    with pytest.raises(
        ValueError,
        match="Invalid grid type in data: {'water_depth'}",
    ):
        component.write()


def test_exposure_grid_component_create(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))

    # Call the method
    component.create(
        exposure_fname="industrial_content",
    )

    # Assert the output
    assert isinstance(component.data, xr.Dataset)
    assert "industrial_content" in component.data.data_vars
    assert component.data.industrial_content.attrs.get(FN__CURVE) == "in2"
    assert component.data.raster.shape == (11, 11)
    # Assert the attributes
    assert isinstance(
        component.data_attrs["industrial_content"],
        ExposureGridVariable,
    )
    assert component.data_attrs["industrial_content"].type == DEFAULT
    assert component.data_attrs["industrial_content"].fn_curve == "in2"

    # Assert entries in the config
    assert component.model.config.data.type == GRID


def test_exposure_grid_component_create_multi(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))

    # Call the method
    component.create(
        exposure_fnames=["industrial_content", "industrial_structure"],
        exposure_link_fname="exposure_grid_link",
        expand=False,
    )

    # Assert the output
    assert "industrial_content" in component.data.data_vars
    assert "industrial_structure" in component.data.data_vars
    assert component.data.industrial_structure.attrs.get(FN__CURVE) == "in1"
    assert component.data_attrs["industrial_structure"].fn_curve == "in1"


def test_exposure_grid_component_create_name(
    model_with_region: FIATModel,
    vulnerability_curves: xr.Dataset,
    vulnerability_identifiers: xr.Dataset,
):
    # Setup the model with only a vulnerability dataset with a custom name
    model_with_region._type = "grid"
    model_with_region.vulnerability.set(
        vulnerability_curves.rename(
            {k: k.replace("default", "custom") for k in vulnerability_curves.variables}
        )
    )
    model_with_region.vulnerability.set_id(
        vulnerability_identifiers.rename(
            {
                k: k.replace("default", "custom")
                for k in vulnerability_identifiers.variables
            }
        )
    )
    # Setup the component
    component = ExposureGridComponent(model=model_with_region)

    # Call the method
    component.create(
        exposure_fnames="industrial_content",
        vulnerability_name="custom",
    )

    # Assert the output
    assert "industrial_content" in component.data.data_vars
    assert component.data.industrial_content.attrs.get(FN__CURVE) == "in2"


def test_exposure_grid_component_create_errors(
    mocker: MockerFixture,
    model: FIATModel,
):
    # Setup the component
    model._type = "grid"
    component = ExposureGridComponent(model=model)

    # Fake component
    fake_component = mocker.Mock()
    fake_component.data.identifiers.empty = False

    # Assert missing region error
    mocker.patch.object(FIATModel, VULNERABILITY, fake_component)
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid"
    ):
        component.create(
            exposure_fnames="industrial_content",
            exposure_link_fname="",
        )


def test_exposure_grid_component_create_name_errors(
    model_exposure_setup: FIATModel,
):
    # Setup the component, the model only contains the default vulnerability dataset
    component = ExposureGridComponent(model=model_exposure_setup("grid"))

    # Assert the vulnerability dataset absent error
    with pytest.raises(
        ValueError,
        match="'custom' does not have any identifiers",
    ):
        component.create(
            exposure_fnames="industrial_content",
            vulnerability_name="custom",
        )


def test_exposure_grid_component_create_categorized(
    model_exposure_setup: FIATModel,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))

    # Call the method
    component.create_categorized(
        exposure_fname="categories",
        name="buildings",
    )

    # Assert the output
    assert "buildings" in component.data.data_vars
    assert component.data.raster.shape == (473, 468)
    # Assert the attributes
    assert component.data_attrs["buildings"].type == CATEGORIZED


def test_exposure_grid_component_create_categorized_name(
    model_with_region: FIATModel,
    vulnerability_curves: xr.Dataset,
    vulnerability_identifiers: xr.Dataset,
):
    # Setup the model with only a vulnerability dataset with a custom name
    model_with_region._type = "grid"
    model_with_region.vulnerability.set(
        vulnerability_curves.rename(
            {k: k.replace("default", "custom") for k in vulnerability_curves.variables}
        )
    )
    model_with_region.vulnerability.set_id(
        vulnerability_identifiers.rename(
            {
                k: k.replace("default", "custom")
                for k in vulnerability_identifiers.variables
            }
        )
    )
    # Setup the component
    component = ExposureGridComponent(model=model_with_region)

    # Call the method
    component.create_categorized(
        exposure_fname="categories",
        name="buildings",
        vulnerability_name="custom",
    )

    # Assert the output
    assert "buildings" in component.data.data_vars
    assert component.data.raster.shape == (473, 468)


def test_exposure_grid_component_create_categorized_errors(
    mocker: MockerFixture, model: FIATModel
):
    # Setup the component
    model._type = "grid"
    component = ExposureGridComponent(model=model)

    # Fake component
    fake_component = mocker.Mock()
    fake_component.data.identifiers.empty = False

    # Assert missing region error
    mocker.patch.object(FIATModel, VULNERABILITY, fake_component)
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid"
    ):
        component.create_categorized(
            exposure_fname="",
        )


def test_exposure_grid_component_create_categorized_name_errors(
    model_exposure_setup: FIATModel,
):
    # Setup the component, the model only contains the default vulnerability dataset
    component = ExposureGridComponent(model=model_exposure_setup("grid"))

    # Assert the vulnerability dataset absent error
    with pytest.raises(
        ValueError,
        match="'custom' does not have any identifiers",
    ):
        component.create_categorized(
            exposure_fname="categories",
            vulnerability_name="custom",
        )


def test_exposure_grid_component_create_categorized_values(
    model_exposure_setup: FIATModel,
    exposure_grid: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))
    # Set data like a dummy
    component._data = exposure_grid["buildings"].to_dataset()
    component._data_attrs = {}

    # Call the method
    component.create_categorized_values(
        exposure_name="buildings",
        exposure_table_fname="category_values",
        index_name=VALUE,
    )

    # Assert the output
    assert "buildings_cat" in component.data.dims
    assert "buildings_structure" in component.data.data_vars
    assert "buildings_cat" in component.data["buildings_structure"].dims
    # Assert the attributes
    assert component.data_attrs["buildings_structure"].type == VALUES
    assert component.data_attrs["buildings_structure"].vulnerability == [DEFAULT]


def test_exposure_grid_component_create_categorized_values_vulnerability_name(
    model_exposure_setup: FIATModel,
    exposure_grid: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))
    # Set data like a dummy
    component._data = exposure_grid["buildings"].to_dataset()
    component._data_attrs = {}

    # Call the method with a vulnerability name
    component.create_categorized_values(
        exposure_name="buildings",
        exposure_table_fname="category_values",
        index_name=VALUE,
        vulnerability_name="default",
    )

    # Assert the attributes
    assert component.data_attrs["buildings_structure"].vulnerability == ["default"]
    assert component.data_attrs["buildings_content"].vulnerability == ["default"]


def test_exposure_grid_component_create_categorized_values_vulnerability_list(
    model_exposure_setup: FIATModel,
    exposure_grid: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))
    # Set data like a dummy
    component._data = exposure_grid["buildings"].to_dataset()
    component._data_attrs = {}

    # Call the method with a list of vulnerability names
    component.create_categorized_values(
        exposure_name="buildings",
        exposure_table_fname="category_values",
        index_name=VALUE,
        vulnerability_name=["default"],
    )

    # Assert the attributes
    assert component.data_attrs["buildings_structure"].vulnerability == ["default"]
    assert component.data_attrs["buildings_content"].vulnerability == ["default"]


def test_exposure_grid_component_create_categorized_values_vulnerability_errors(
    model_exposure_setup: FIATModel,
    exposure_grid: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))
    # Set data like a dummy
    component._data = exposure_grid["buildings"].to_dataset()
    component._data_attrs = {}

    # Assert the error when one of the vulnerability datasets is absent
    with pytest.raises(
        RuntimeError,
        match="Choose from already present data variables",
    ):
        component.create_categorized_values(
            exposure_name="buildings",
            exposure_table_fname="category_values",
            index_name=VALUE,
            vulnerability_name=["default", "foo"],
        )


def test_exposure_grid_component_create_categorized_values_name_prefix(
    model_exposure_setup: FIATModel,
    exposure_grid: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))
    # Set data like a dummy
    component._data = exposure_grid["buildings"].to_dataset()
    component._data_attrs = {}

    # Call the method with a name prefix
    component.create_categorized_values(
        exposure_name="buildings",
        exposure_table_fname="category_values",
        index_name=VALUE,
        name_prefix="foo",
    )

    # Assert the output, the prefix is part of the variable names
    assert "buildings_foo_structure" in component.data.data_vars
    assert "buildings_foo_content" in component.data.data_vars
    assert "buildings_structure" not in component.data.data_vars
    # Assert the attributes
    assert component.data_attrs["buildings_foo_structure"].type == VALUES
    assert component.data_attrs["buildings_foo_content"].type == VALUES


def test_exposure_grid_component_create_categorized_values_table(
    model_exposure_setup: FIATModel,
    exposure_grid: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))
    # Set data like a dummy
    component._data = exposure_grid["buildings"].to_dataset()
    component._data_attrs = {}

    # Call the method
    component.create_categorized_values(
        exposure_name="buildings",
        exposure_table={1: 200, 2: 300, 3: 400, 4: 100},
        index_name=INDEX,
    )

    # Assert the output
    assert "buildings_cat" in component.data.dims
    assert "buildings_value" in component.data.data_vars
    assert "buildings_cat" in component.data["buildings_value"].dims


def test_exposure_grid_component_create_categorized_values_no_table(
    model_exposure_setup: FIATModel,
    exposure_grid: xr.Dataset,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))
    # Set data like a dummy
    component._data = exposure_grid["buildings"].to_dataset()
    component._data_attrs = {}

    # Call the method
    component.create_categorized_values(
        exposure_name="buildings",
    )

    # Assert the output
    assert "buildings_cat" in component.data.dims
    assert "buildings_value" in component.data.data_vars
    assert "buildings_cat" in component.data["buildings_value"].dims
    assert component.data["buildings_value"].values[0] == 0
    np.testing.assert_almost_equal(
        component.data["buildings_value"].values[1:].mean(),
        100,
        decimal=0,
    )


def test_exposure_grid_component_create_from_geom(
    model_exposure_setup: FIATModel,
    exposure_vector: gpd.GeoDataFrame,
):
    # Setup the component
    component = ExposureGridComponent(model=model_exposure_setup("grid"))

    # Call the method
    component.create_grid(res=10)
    component.create_from_geom(
        exposure_fname=exposure_vector,
        column="max_damage_structure",
        curve="commercial_structure",
        name="commercial_structure",
        **{"object_type": "commercial"},
    )

    # Assert the outout
    assert "commercial_structure" in component.data.data_vars


def test_exposure_grid_component_create_from_geom_name(
    model_with_region: FIATModel,
    vulnerability_curves: xr.Dataset,
    vulnerability_identifiers: xr.Dataset,
    exposure_vector: gpd.GeoDataFrame,
):
    # Setup the model with only a vulnerability dataset with a custom name
    model_with_region._type = "grid"
    model_with_region.vulnerability.set(
        vulnerability_curves.rename(
            {k: k.replace("default", "custom") for k in vulnerability_curves.variables}
        )
    )
    model_with_region.vulnerability.set_id(
        vulnerability_identifiers.rename(
            {
                k: k.replace("default", "custom")
                for k in vulnerability_identifiers.variables
            }
        )
    )
    # Setup the component
    component = ExposureGridComponent(model=model_with_region)

    # Call the method
    component.create_grid(res=10)
    component.create_from_geom(
        exposure_fname=exposure_vector,
        column="max_damage_structure",
        curve="commercial_structure",
        name="commercial_structure",
        vulnerability_name="custom",
        **{"object_type": "commercial"},
    )

    # Assert the outout
    assert "commercial_structure" in component.data.data_vars


def test_exposure_grid_component_create_from_geom_errors(
    mocker: MockerFixture,
    model: FIATModel,
):
    # Setup the component
    model._type = "grid"
    component = ExposureGridComponent(model=model)

    # Fake component
    fake_component = mocker.Mock()
    fake_component.data.identifiers.empty = False

    # Assert missing region error
    mocker.patch.object(FIATModel, VULNERABILITY, fake_component)
    with pytest.raises(
        MissingRegionError, match="Region is required for setting up exposure grid"
    ):
        component.create_from_geom(
            exposure_fname="",
            column="",
            curve="",
        )

    mocker.patch.object(FIATModel, "region", mocker.Mock())
    # Assert error when no spatial dimensions are known
    with pytest.raises(
        RuntimeError, match="An existing grid definition is needed for this method"
    ):
        component.create_from_geom(
            exposure_fname="",
            column="",
            curve="",
        )


def test_exposure_grid_component_create_from_geom_name_errors(
    model_exposure_setup: FIATModel,
):
    # Setup the component, the model only contains the default vulnerability dataset
    component = ExposureGridComponent(model=model_exposure_setup("grid"))

    # Assert the vulnerability dataset absent error
    with pytest.raises(
        ValueError,
        match="'custom' does not have any identifiers",
    ):
        component.create_from_geom(
            exposure_fname="",
            column="",
            curve="",
            vulnerability_name="custom",
        )
