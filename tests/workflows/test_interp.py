from typing import Callable

import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator

from hydromt_fiat.workflows.interp import (
    bound_monotone_nd,
    combine_1d_to_nd,
    refine_nd_grid,
)


def test_combine_1d_to_nd_product(
    interp_axes: list[np.ndarray],
    interp_values: list[np.ndarray],
):
    # Call the function
    out = combine_1d_to_nd(interp_axes, interp_values)

    # Assert the output
    assert out.shape == (1, 3, 2)
    assert out[0, 1, 1] == 0.5


def test_combine_1d_to_nd_union(
    interp_axes: list[np.ndarray],
    interp_values: list[np.ndarray],
):
    # Call the function
    out = combine_1d_to_nd(interp_axes, interp_values, rule="union")

    # Assert the output
    assert out[0, 1, 1] == 1.0
    assert out[0, 1, 0] == 0.5


def test_combine_1d_to_nd_mean(
    interp_axes: list[np.ndarray],
    interp_values: list[np.ndarray],
):
    # Call the function with weights
    out = combine_1d_to_nd(
        interp_axes, interp_values, rule="mean", weights=[0.25, 0.75]
    )

    # Assert the output
    assert out[0, 2, 0] == 0.25


def test_combine_1d_to_nd_mean_errors(
    interp_axes: list[np.ndarray],
    interp_values: list[np.ndarray],
):
    # Assert the error of weights that do not sum up to one
    with pytest.raises(ValueError, match="weights"):
        combine_1d_to_nd(interp_axes, interp_values, rule="mean", weights=[0.5, 0.6])


def test_combine_1d_to_nd_geometric(
    interp_axes: list[np.ndarray],
    interp_values: list[np.ndarray],
):
    # Call the function
    out = combine_1d_to_nd(interp_axes, interp_values, rule="geometric")

    # Assert the output
    np.testing.assert_allclose(out[0, 1, 1], 0.5**0.5)


def test_combine_1d_to_nd_isoline():
    # Setup the axes and values
    axes = [np.linspace(0, 2, 5), np.linspace(0, 10, 5)]
    values = [np.array([np.linspace(0, 1, 5) ** 2]), np.array([np.linspace(0, 1, 5)])]

    # Call the function
    out = combine_1d_to_nd(axes, values, rule="isoline")

    # Assert on the edges the field equals the input along that axis
    np.testing.assert_allclose(out[0, :, 0], values[0][0], atol=1e-6)
    np.testing.assert_allclose(out[0, 0, :], values[1][0], atol=1e-6)
    # Assert the shape and bounds
    assert out.shape == (1, 5, 5)
    assert (out >= 0).all()
    assert (out <= 1).all()


def test_combine_1d_to_nd_blend(
    interp_axes: list[np.ndarray],
    interp_values: list[np.ndarray],
):
    # Call the function with a value for the corner
    out = combine_1d_to_nd(interp_axes, interp_values, rule="blend", corner=0.8)

    # Assert the corner and that the edges equal the input
    assert out[0, -1, -1] == pytest.approx(0.8)
    np.testing.assert_allclose(out[0, :, 0], interp_values[0][0])
    np.testing.assert_allclose(out[0, 0, :], interp_values[1][0])


def test_combine_1d_to_nd_anchored():
    # Setup the axes and values
    axes = [np.array([0.0, 1.0, 2.0]), np.array([0.0, 5.0, 10.0])]
    values = [np.array([[0.0, 0.5, 1.0]]), np.array([[0.0, 0.5, 1.0]])]

    # Call the function with an anchor point
    out = combine_1d_to_nd(axes, values, rule="anchored", points=[[1, 5, 0.9]])

    # Assert the anchor point and that the edges are kept
    assert out[0, 1, 1] == pytest.approx(0.9, abs=1e-6)
    np.testing.assert_allclose(out[0, :, 0], values[0][0], atol=1e-6)
    np.testing.assert_allclose(out[0, 0, :], values[1][0], atol=1e-6)


def test_combine_1d_to_nd_errors(
    interp_axes: list[np.ndarray],
    interp_values: list[np.ndarray],
):
    # Assert the errors
    with pytest.raises(ValueError, match="At least two"):
        combine_1d_to_nd(interp_axes[:1], interp_values[:1])

    with pytest.raises(ValueError, match="strictly increasing"):
        combine_1d_to_nd([interp_axes[0][::-1], interp_axes[1]], interp_values)

    with pytest.raises(ValueError, match="shape"):
        combine_1d_to_nd(interp_axes, [interp_values[0][0], interp_values[1]])

    with pytest.raises(ValueError, match="shape"):
        combine_1d_to_nd(interp_axes, [interp_values[0][:, :-1], interp_values[1]])

    with pytest.raises(ValueError, match="Unknown rule"):
        combine_1d_to_nd(interp_axes, interp_values, rule="nope")

    with pytest.raises(ValueError, match="exactly two"):
        combine_1d_to_nd(
            [*interp_axes, np.array([0.0, 1.0])],
            [*interp_values, np.array([[0.0, 1.0]])],
            rule="blend",
        )


def test_refine_nd_grid(
    interp_axes: list[np.ndarray],
    interp_geometric: Callable[[list[np.ndarray]], np.ndarray],
):
    # Call the function
    refined = refine_nd_grid(interp_axes, interp_geometric, tolerance=1e-3)

    # Assert the axes are refined
    assert len(refined[0]) > 3
    assert len(refined[1]) > 2
    # Assert linear interpolation on the refined grid is close to the exact field
    dense = [np.linspace(0, 2, 41), np.linspace(0, 10, 41)]
    exact = interp_geometric(dense)[0]
    interp = RegularGridInterpolator(refined, interp_geometric(refined)[0])
    pts = np.stack(np.meshgrid(*dense, indexing="ij"), axis=-1)
    assert np.abs(interp(pts) - exact).max() < 5e-3


def test_refine_nd_grid_exact(
    interp_axes: list[np.ndarray],
    interp_values: list[np.ndarray],
):
    # Call the function with a field that is exact (linear) on the axes
    refined = refine_nd_grid(
        interp_axes,
        lambda grid: combine_1d_to_nd(interp_axes, interp_values, grid=grid),
    )

    # Assert the axes are unchanged
    for new, old in zip(refined, interp_axes, strict=True):
        np.testing.assert_array_equal(new, old)


def test_refine_nd_grid_max_points(
    interp_axes: list[np.ndarray],
    interp_geometric: Callable[[list[np.ndarray]], np.ndarray],
):
    # Call the function with a tolerance that cannot be reached
    refined = refine_nd_grid(
        interp_axes, interp_geometric, tolerance=1e-9, max_points=4
    )

    # Assert the number of points is limited
    assert all(len(item) <= 4 for item in refined)


def test_bound_monotone_nd():
    # Call the function with values outside of the bounds
    field, changed = bound_monotone_nd(np.array([[0.0, -0.1, 1.2]]), dims=[1])

    # Assert the values are clipped
    np.testing.assert_array_equal(field, [[0.0, 0.0, 1.0]])
    assert changed

    # Call the function with valid values
    valid = np.array([[0.0, 0.5, 1.0]])
    field, changed = bound_monotone_nd(valid, dims=[1])

    # Assert nothing is changed
    np.testing.assert_array_equal(field, valid)
    assert not changed

    # Call the function with decreasing values
    field, _ = bound_monotone_nd(np.array([[0.2, 0.1, 0.5]]), dims=[1])

    # Assert the values are lifted
    np.testing.assert_array_equal(field, [[0.2, 0.2, 0.5]])
