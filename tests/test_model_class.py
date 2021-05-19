"""Test FIAT plugin model class against hydromt.models.model_api"""


from hydromt.models import MODELS
from hydromt.cli.cli_utils import parse_config
from os.path import join, dirname, abspath
import logging
import numpy as np
import pytest


TESTDATADIR = join(dirname(abspath(__file__)), "data")
EXAMPLEDIR = join(dirname(abspath(__file__)), "..", "examples")


_models = {
    "fiat": {
        "example": join("results", "fiat_test"),
        "ini": "build_fiat.ini",
    },
}


@pytest.mark.parametrize("model", list(_models.keys()))
def test_model_class(model):
    _model = _models[model]

    # Read model in examples folder.
    root = join(EXAMPLEDIR, _model["example"])
    mod = MODELS.get(model)(root=root, mode="r")
    mod.read()

    # Run test_model_api() method.
    non_compliant_list = mod.test_model_api()
    assert len(non_compliant_list) == 0


@pytest.mark.parametrize("model", list(_models.keys()))
def test_model_build(tmpdir, model):
    logger = logging.getLogger(__name__)
    _model = _models[model]
    # root = str(tmpdir.join(model))
    root = join(
        EXAMPLEDIR, _model["example"]
    )  # TODO: Update the example folder after the implementation is finished!

    # Initialize model.
    yml = join(
        EXAMPLEDIR, "data_catalog.yml"
    )  # TODO: Join with deltares data and create artifacts!
    mod1 = MODELS.get(model)(root=root, mode="w", logger=logger, data_libs=yml)

    # Build model.
    region = {"grid": join(EXAMPLEDIR, "data", "hazard", "RP_2.tif")}
    config = join(EXAMPLEDIR, _model["ini"])
    opt = parse_config(config)
    mod1.build(region=region, opt=opt)

    # Check if model is api compliant.
    non_compliant_list = mod1.test_model_api()
    assert len(non_compliant_list) == 0

    # Read the created model together with the model from the examples folder.
    root0 = join(EXAMPLEDIR, _model["example"])
    mod0 = MODELS.get(model)(root=root0, mode="r")
    mod0.read()
    mod1 = MODELS.get(model)(root=root, mode="r")
    mod1.read()

    # Compare model maps.
    invalid_maps = {}
    if len(mod0._staticmaps) > 0:
        maps = mod0.staticmaps.raster.vars
        assert np.all(mod0.crs == mod1.crs), f"map crs staticmaps"
        for name in maps:
            map0 = mod0.staticmaps[name].fillna(0)
            map1 = mod1.staticmaps[name].fillna(0)
            if not np.allclose(map0, map1):
                notclose = ~np.isclose(map0, map1)
                xy = map0.raster.idx_to_xy(np.where(notclose.ravel())[0])
                ncells = int(np.sum(notclose))
                diff = (map0 - map1).values[notclose].mean()
                xys = ", ".join([f"({x:.6f}, {y:.6f})" for x, y in zip(*xy)])
                invalid_maps[name] = f"diff: {diff:.4f} ({ncells:d} cells: [{xys}])"
                invalid_maps.append(name)

    assert len(invalid_maps) == 0, f"invalid maps: {invalid_maps}"

    # Compare model geometries.
    if mod0._staticgeoms:
        for name in mod0.staticgeoms:
            geom0 = mod0.staticgeoms[name]
            geom1 = mod1.staticgeoms[name]
            assert geom0.index.size == geom1.index.size and np.all(
                geom0.index == geom1.index
            ), f"geom index {name}"
            assert geom0.columns.size == geom1.columns.size and np.all(
                geom0.columns == geom1.columns
            ), f"geom columns {name}"
            assert geom0.crs == geom1.crs, f"geom crs {name}"
            assert np.all(geom0.geometry == geom1.geometry), f"geom {name}"

    # Compare model configs.
    if mod0._config:
        mod0.set_root(mod1.root)
        assert mod0._config == mod1._config, f"config mismatch"
