"""
Verifies that the frontend cubic spline algorithm (ported to Python)
agrees with scipy's CubicSpline(bc_type='natural') to within floating-point
tolerance. Both claim to implement natural cubic splines, so their outputs
should be identical up to numerical precision.
"""
import numpy as np
import pytest
from scipy.interpolate import CubicSpline


def _frontend_cubic_spline(t, values, new_t):
    """
    Python port of the JS cubicSpline() function in writer-scripts.js.
    Natural cubic spline using the tridiagonal (Thomas) algorithm.
    """
    n = len(t) - 1
    h = [t[i + 1] - t[i] for i in range(n)]

    alpha = [0.0] * n
    for i in range(1, n):
        alpha[i] = (3 / h[i]) * (values[i + 1] - values[i]) - (3 / h[i - 1]) * (values[i] - values[i - 1])

    l = [0.0] * (n + 1)
    mu = [0.0] * (n + 1)
    z = [0.0] * (n + 1)

    l[0] = 1.0
    for i in range(1, n):
        l[i] = 2 * (t[i + 1] - t[i - 1]) - h[i - 1] * mu[i - 1]
        mu[i] = h[i] / l[i]
        z[i] = (alpha[i] - h[i - 1] * z[i - 1]) / l[i]
    l[n] = 1.0

    c = [0.0] * (n + 1)
    b = [0.0] * n
    d = [0.0] * n

    for j in range(n - 1, -1, -1):
        c[j] = z[j] - mu[j] * c[j + 1]
        b[j] = (values[j + 1] - values[j]) / h[j] - h[j] * (c[j + 1] + 2 * c[j]) / 3
        d[j] = (c[j + 1] - c[j]) / (3 * h[j])

    result = []
    for ti in new_t:
        i = next(
            (idx for idx in range(n) if t[idx] <= ti <= t[idx + 1]),
            n - 1
        )
        dt = ti - t[i]
        result.append(values[i] + b[i] * dt + c[i] * dt**2 + d[i] * dt**3)
    return result


@pytest.mark.parametrize("knots,values", [
    ([0, 1, 2, 3], [0.0, 0.5, 0.2, 0.8]),
    ([0, 0.1, 0.15, 0.3], [0.0, 0.05, -0.03, 0.12]),
    ([0, 1, 2, 3, 4, 5], [0.0, 0.1, -0.05, 0.2, 0.08, 0.0]),
])
def test_frontend_matches_scipy(knots, values):
    t = knots
    new_t = np.linspace(t[0], t[-1], 200)

    scipy_cs = CubicSpline(t, values, bc_type='natural')
    scipy_vals = scipy_cs(new_t)

    frontend_vals = _frontend_cubic_spline(t, values, new_t.tolist())

    max_diff = np.max(np.abs(np.array(frontend_vals) - scipy_vals))
    assert max_diff < 1e-10, f"Max difference {max_diff} exceeds tolerance"
