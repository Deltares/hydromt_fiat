"""Test FIAT plugin model class against hydromt.models.model_api"""

from hydromt.cli.cli_utils import parse_config
from hydromt_fiat import FiatModel
from os.path import join, dirname, abspath
import logging
import numpy as np
import pytest

EXAMPLEDIR = join(dirname(abspath(__file__)), "..", "examples")

_cases = {
    "fiat_flood": {
        "region_grid": join("data", "flood_hand", "hand_050cm_rp02.tif"),
        "example": "fiat_flood",
        "ini": "fiat_flood.ini",
    },
}


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_model_class(case):
    # Read model in examples folder.
    root = join(EXAMPLEDIR, _cases[case]["example"])
    mod = FiatModel(root=root, mode="r")
    mod.read()

    # Run test_model_api() method.
    non_compliant_list = mod.test_model_api()
    assert len(non_compliant_list) == 0


@pytest.mark.parametrize("case", list(_cases.keys()))
def test_model_build(tmpdir, case):
    logger = logging.getLogger(__name__)
    _case = _cases[case]
    root = str(tmpdir.join(case))

    # Build model.
    region = {"grid": join(EXAMPLEDIR, _case["region_grid"])}
    opt = parse_config(join(EXAMPLEDIR, _case["ini"]))
    kwargs = opt.pop("global", {})  # pas global section to model init
    mod1 = FiatModel(root=root, mode="w", logger=logger, **kwargs)
    mod1.build(region=region, opt=opt)

    # Check if model is api compliant.
    non_compliant_list = mod1.test_model_api()
    assert len(non_compliant_list) == 0

    # Read the created model together with the model from the examples folder.
    root0 = join(EXAMPLEDIR, _case["example"])
    mod0 = FiatModel(root=root0, mode="r")
    mod0.read()
    mod1 = FiatModel(root=root, mode="r")
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
        mod1.set_root(mod1.root)
        assert mod0._config == mod1._config, f"config mismatch"