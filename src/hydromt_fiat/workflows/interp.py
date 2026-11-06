"""Interpolation workflows, e.g. combining 1D functions into an nD field."""

from collections.abc import Callable
from typing import Any

import numpy as np
from scipy.interpolate import RBFInterpolator, RegularGridInterpolator

__all__ = [
    "COMBINE_RULES",
    "bound_monotone_nd",
    "combine_1d_to_nd",
    "refine_nd_grid",
]


def _expand(
    values: np.ndarray,
    axis: int,
    ndim: int,
) -> np.ndarray:
    """Shape (batch, n) values such that they broadcast along `axis` of nD fields."""
    shape = [values.shape[0]] + [1] * ndim
    shape[axis + 1] = values.shape[1]
    return values.reshape(shape)


def _normalize(
    axis: np.ndarray,
) -> np.ndarray:
    """Scale an axis to the range 0 to 1."""
    return (axis - axis[0]) / (axis[-1] - axis[0])


def _weights(
    weights: list[float] | None,
    n: int,
) -> np.ndarray:
    """Validate the weights, equal weights by default."""
    # Use equal weights if not provided
    if weights is None:
        return np.full(n, 1 / n)
    # Check the weights
    weights_array = np.asarray(weights, dtype=float)
    if (
        weights_array.shape != (n,)
        or (weights_array < 0).any()
        or not np.isclose(weights_array.sum(), 1)
    ):
        raise ValueError(
            f"The weights should be {n} values that are not negative and sum to 1"
        )
    return weights_array


def _rule_product(
    grid: list[np.ndarray],
    values: list[np.ndarray],
) -> np.ndarray:
    """Multiply the functions."""
    out = np.asarray(1.0)
    for axis, item in enumerate(values):
        out = out * _expand(item, axis, len(grid))
    return out


def _rule_union(
    grid: list[np.ndarray],
    values: list[np.ndarray],
) -> np.ndarray:
    """Combine the functions as independent probabilities (either one occurs)."""
    out = np.asarray(1.0)
    for axis, item in enumerate(values):
        out = out * (1 - _expand(item, axis, len(grid)))
    return 1 - out


def _rule_mean(
    grid: list[np.ndarray],
    values: list[np.ndarray],
    weights: list[float] | None = None,
) -> np.ndarray:
    """Take the (weighted) arithmetic mean of the functions."""
    weights_array = _weights(weights, len(values))
    out = np.asarray(0.0)
    for axis, item in enumerate(values):
        out = out + weights_array[axis] * _expand(item, axis, len(grid))
    return out


def _rule_geometric(
    grid: list[np.ndarray],
    values: list[np.ndarray],
    weights: list[float] | None = None,
) -> np.ndarray:
    """Take the (weighted) geometric mean of the functions."""
    weights_array = _weights(weights, len(values))
    out = np.asarray(1.0)
    for axis, item in enumerate(values):
        out = out * _expand(item, axis, len(grid)) ** weights_array[axis]
    return out


def _first_crossing(
    xs: np.ndarray,
    values: np.ndarray,
    level: np.ndarray,
) -> np.ndarray:
    """Smallest x where the (running maximum of the) values reach the level."""
    # Make the function non-decreasing, so the crossing is unique
    running = np.maximum.accumulate(values)
    # Get the interval in which the level is reached
    idx = np.searchsorted(running, level, side="left")
    inside = idx < len(xs)
    idx_hi = np.minimum(idx, len(xs) - 1)
    idx_lo = np.maximum(idx - 1, 0)
    # Linear interpolation within the interval, flat intervals are left at the start
    span = running[idx_hi] - running[idx_lo]
    frac = np.divide(
        level - running[idx_lo], span, out=np.zeros_like(level), where=span > 0
    )
    x = xs[idx_lo] + frac * (xs[idx_hi] - xs[idx_lo])
    x = np.where(idx == 0, xs[0], x)
    # Set the levels that are never reached infinitely far away
    return np.where(inside, x, np.inf)


def _rule_isoline(
    grid: list[np.ndarray],
    values: list[np.ndarray],
    p: float = 2.0,
) -> np.ndarray:
    """Construct the isolines from the functions, with a p-norm between the axes.

    The value of a point is the level at which the point lies on the isoline. The
    isoline of a level crosses each axis where the function of that axis reaches the
    level.
    """
    ndim = len(grid)
    batch = values[0].shape[0]
    shape = (batch, *[len(item) for item in grid])
    # Get the distance of the grid points from the start of each axis
    offsets = [
        _expand((item - item[0])[None, :], axis, ndim) for axis, item in enumerate(grid)
    ]

    # Find the level per point by bisection, as the levels are between 0 and 1
    lo = np.zeros(shape)
    hi = np.ones(shape)
    for _ in range(50):
        mid = (lo + hi) / 2
        total = np.zeros(shape)
        for axis in range(ndim):
            # Get where the isoline of the level crosses the axis
            crossing = np.empty(shape)
            for b in range(batch):
                crossing[b] = _first_crossing(
                    grid[axis] - grid[axis][0], values[axis][b], mid[b]
                )
            x = np.broadcast_to(offsets[axis], shape)
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(
                    x == 0, 0.0, np.where(crossing > 0, x / crossing, np.inf)
                )
            total = total + ratio**p
        # Raise the level where the sum is above one, as it decreases with the level
        too_low = total > 1
        lo = np.where(too_low, mid, lo)
        hi = np.where(too_low, hi, mid)
    return (lo + hi) / 2


def _blend_edges(
    grid: list[np.ndarray],
    values: list[np.ndarray],
    corner: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Get the edges of the 2D patch: y start, y end, x start and x end."""
    f1, f2 = values
    u = _normalize(grid[0])[None, :]
    v = _normalize(grid[1])[None, :]
    # Get the edges: the start edges are the functions, the end edges run linearly
    # to the corner
    y0 = f1
    y1 = f2[:, -1:] + u * (corner - f2[:, -1:])
    x0 = f2
    x1 = f1[:, -1:] + v * (corner - f1[:, -1:])
    return y0, y1, x0, x1


def _rule_blend(
    grid: list[np.ndarray],
    values: list[np.ndarray],
    corner: float = 1.0,
) -> np.ndarray:
    """Blend the functions (Coons patch) with the value of the far corner."""
    f1, f2 = values
    y0, y1, x0, x1 = _blend_edges(grid, values, corner)
    u = _normalize(grid[0])[None, :, None]
    v = _normalize(grid[1])[None, None, :]
    # Get the four corners of the patch
    c00 = f1[:, :1, None]
    c10 = f1[:, -1:, None]
    c01 = f2[:, None, -1:]
    c11 = corner
    # Interpolate between the edges and remove the double counted corners
    return (
        (1 - v) * y0[:, :, None]
        + v * y1[:, :, None]
        + (1 - u) * x0[:, None, :]
        + u * x1[:, None, :]
        - ((1 - u) * (1 - v) * c00 + u * (1 - v) * c10)
        - ((1 - u) * v * c01 + u * v * c11)
    )


def _rule_anchored(
    grid: list[np.ndarray],
    values: list[np.ndarray],
    points: list[list[float]] | None = None,
    kernel: str = "thin_plate_spline",
    corner: float = 1.0,
) -> np.ndarray:
    """Interpolate the edges and anchor points (x, y, value) with radial basis."""
    y0, y1, x0, x1 = _blend_edges(grid, values, corner)
    gx = _normalize(grid[0])
    gy = _normalize(grid[1])

    # Scale the anchor points like the grid
    anchors = np.asarray(points if points is not None else [], dtype=float)
    anchors = anchors.reshape(-1, 3)
    anchor_xy = np.column_stack(
        [
            (anchors[:, 0] - grid[0][0]) / (grid[0][-1] - grid[0][0]),
            (anchors[:, 1] - grid[1][0]) / (grid[1][-1] - grid[1][0]),
        ]
    )
    # Get the points to interpolate to
    xx, yy = np.meshgrid(gx, gy, indexing="ij")
    targets = np.column_stack([xx.ravel(), yy.ravel()])

    out = np.empty((values[0].shape[0], len(gx), len(gy)))
    for b in range(out.shape[0]):
        # Get the samples on the four edges (the corners are the same sample)
        samples = {}
        for i, x in enumerate(gx):
            samples[(x, 0.0)] = y0[b, i]
            samples[(x, 1.0)] = y1[b, i]
        for j, y in enumerate(gy):
            samples.setdefault((0.0, y), x0[b, j])
            samples.setdefault((1.0, y), x1[b, j])
        xy = np.array(list(samples.keys()))
        val = np.array(list(samples.values()))
        # An anchor replaces the edge sample at the same location
        if len(anchors) > 0:
            dist = np.linalg.norm(xy[:, None, :] - anchor_xy[None, :, :], axis=-1)
            keep = (dist > 1e-9).all(axis=1)
            xy = np.vstack([xy[keep], anchor_xy])
            val = np.concatenate([val[keep], anchors[:, 2]])
        out[b] = RBFInterpolator(xy, val, kernel=kernel)(targets).reshape(xx.shape)
    return out


COMBINE_RULES: dict[str, Callable[..., np.ndarray]] = {
    "product": _rule_product,
    "union": _rule_union,
    "mean": _rule_mean,
    "geometric": _rule_geometric,
    "isoline": _rule_isoline,
    "blend": _rule_blend,
    "anchored": _rule_anchored,
}


def combine_1d_to_nd(
    axes: list[np.ndarray],
    values: list[np.ndarray],
    *,
    rule: str = "product",
    grid: list[np.ndarray] | None = None,
    **kwargs: Any,
) -> np.ndarray:
    """Combine one dimensional functions into one n-dimensional field.

    Parameters
    ----------
    axes : list[np.ndarray]
        The axes (strictly increasing) of the one dimensional functions.
    values : list[np.ndarray]
        The values of the functions, each of shape (batch, len(axis)). The batch is
        e.g. the number of curves.
    rule : str, optional
        The rule to combine the functions with, one of `COMBINE_RULES`.
        By default 'product'.
    grid : list[np.ndarray], optional
        The axes of the resulting field. The functions are linearly interpolated onto
        these (constant outside). By default the `axes`.
    **kwargs : dict
        Extra arguments for the rule.

    Returns
    -------
    np.ndarray
        The field of shape (batch, *[len(axis) for axis in grid]).
    """
    # Check the input
    if len(axes) < 2 or len(axes) != len(values):
        raise ValueError("At least two functions (with equal axes and values) needed")
    if rule not in COMBINE_RULES:
        raise ValueError(f"Unknown rule: '{rule}', choose from {list(COMBINE_RULES)}")
    if rule in ("blend", "anchored") and len(axes) != 2:
        raise ValueError(f"Rule '{rule}' needs exactly two functions")
    axes = [np.asarray(item, dtype=float) for item in axes]
    values = [np.asarray(item, dtype=float) for item in values]
    for axis, item in zip(axes, values, strict=True):
        if axis.ndim != 1 or len(axis) < 2 or (np.diff(axis) <= 0).any():
            raise ValueError("The axes should be strictly increasing")
        if item.ndim != 2 or item.shape[1] != len(axis):
            raise ValueError("The values should be of shape (batch, len(axis))")

    # Default to the axes of the functions themselves
    if grid is None:
        grid = axes
    grid = [np.asarray(item, dtype=float) for item in grid]

    # Evaluate the functions on the grid, constant outside of the axes
    evaluated = [
        np.stack([np.interp(g, axis, row) for row in item])
        for axis, item, g in zip(axes, values, grid, strict=True)
    ]

    # Combine them with the rule
    return COMBINE_RULES[rule](grid, evaluated, **kwargs)


def refine_nd_grid(
    axes: list[np.ndarray],
    fn: Callable[[list[np.ndarray]], np.ndarray],
    *,
    tolerance: float = 1e-3,
    max_points: int = 100,
) -> list[np.ndarray]:
    """Refine the axes of a grid until linear interpolation is accurate enough.

    Midpoints are added to the intervals where the field (`fn`) at the midpoints
    deviates more than `tolerance` from the linear interpolation of the field on the
    current grid.

    Parameters
    ----------
    axes : list[np.ndarray]
        The starting axes.
    fn : Callable[[list[np.ndarray]], np.ndarray]
        The function that evaluates the field on a grid (list of axes), returning an
        array of shape (batch, *[len(axis) for axis in grid]).
    tolerance : float, optional
        The maximum absolute deviation, by default 1e-3.
    max_points : int, optional
        The maximum number of points per axis, by default 100.

    Returns
    -------
    list[np.ndarray]
        The refined axes.
    """
    axes = [np.asarray(item, dtype=float) for item in axes]
    ndim = len(axes)
    while True:
        # Get the field on the current grid
        field = fn(axes)

        # Get the grid including the midpoints of every interval
        mids = [(item[:-1] + item[1:]) / 2 for item in axes]
        augmented = []
        for item, mid in zip(axes, mids, strict=True):
            aug = np.empty(len(item) + len(mid))
            aug[0::2] = item
            aug[1::2] = mid
            augmented.append(aug)

        # Get the deviation of the linear interpolation from the field on that grid
        exact = fn(augmented)
        interp = RegularGridInterpolator(axes, np.moveaxis(field, 0, -1))
        points = np.stack(np.meshgrid(*augmented, indexing="ij"), axis=-1)
        approx = np.moveaxis(interp(points), -1, 0)
        error = np.abs(exact - approx).max(axis=0)

        # Add the midpoints of the intervals that deviate too much, worst first
        inserted = False
        for axis in range(ndim):
            # Get the error of an interval, over all the points in its midpoint slab
            slab = np.moveaxis(error, axis, 0)[1::2].reshape(len(mids[axis]), -1)
            interval_error = slab.max(axis=1)
            capacity = max_points - len(axes[axis])
            flagged = np.flatnonzero(interval_error > tolerance)
            flagged = flagged[np.argsort(-interval_error[flagged])][: max(capacity, 0)]
            if len(flagged) > 0:
                axes[axis] = np.sort(np.concatenate([axes[axis], mids[axis][flagged]]))
                inserted = True
        # Return when nothing is left to refine
        if not inserted:
            return axes


def bound_monotone_nd(
    field: np.ndarray,
    dims: list[int],
    *,
    lower: float = 0.0,
    upper: float = 1.0,
) -> tuple[np.ndarray, bool]:
    """Bound a field and make it non-decreasing along the given dimensions.

    Parameters
    ----------
    field : np.ndarray
        The field.
    dims : list[int]
        The dimensions (axes of the array) along which the field is non-decreasing.
    lower : float, optional
        The lower bound, by default 0.
    upper : float, optional
        The upper bound, by default 1.

    Returns
    -------
    tuple[np.ndarray, bool]
        The adjusted field and whether any value was changed.
    """
    # Bound the values
    out = np.clip(field, lower, upper)
    # Lift decreasing values along every dimension
    for dim in dims:
        out = np.maximum.accumulate(out, axis=dim)
    return out, bool(np.abs(out - field).max() > 1e-9)
