import pytest
from hydromt.model.components import GridComponent

from hydromt_fiat.fiat import FIATModel


def test_setup_hazard(tmpdir):
    m = FIATModel(root=tmpdir)
    grid_component = GridComponent(model=m)
    m.add_component("hazard_grid", grid_component)

    with pytest.raises(
        ValueError, match="Cannot perform risk analysis without return periods."
    ):
        m.setup_hazard(hazard_fname="test.nc", risk=True)

    with pytest.raises(
        ValueError, match="Return periods do not match the number of hazard files"
    ):
        m.setup_hazard(
            hazard_fname=["test1.nc", "test2.nc"], risk=True, return_period=[1, 2, 3]
        )
