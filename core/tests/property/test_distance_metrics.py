"""Property-based tests for cosine similarity and angular distance metrics.

These properties were originally exercised only by the standalone
``core/scripts/benchmark_suite.py`` script. Promoting them to pytest +
hypothesis makes regressions detectable in CI.

Properties verified:
1. cosine(a, a) == 1.0 (identity / idempotence)
2. cosine(a, b) == cosine(b, a) (symmetry)
3. -1.0 <= cosine(a, b) <= 1.0 (bounds)
4. arccos(cosine(.,.)) satisfies the triangle inequality
   (i.e. d(a, c) <= d(a, b) + d(b, c) up to numerical tolerance)
5. classify_zone is monotonic on the unit interval and returns one
   of the documented GalacticZone values.
"""
from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from whitemagic.core.memory.galactic_map import GalacticZone, classify_zone

# A reasonable embedding dimension for property tests; small enough
# that hypothesis can shrink quickly, large enough that floating point
# is not pathological.
DIM = 64
COS_TOL = 1e-9


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    raw = dot / (na * nb)
    # Clamp to handle floating-point overshoot before acos().
    return max(-1.0, min(1.0, raw))


def _angular_distance(a: list[float], b: list[float]) -> float:
    return math.acos(_cosine(a, b))


# Strategy: vectors of fixed dimension with bounded floats.  We exclude
# all-zero vectors because cosine is undefined at the origin and
# WhiteMagic embeddings are normalized away from zero in practice.
def _nonzero_vector():
    return st.lists(
        st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=DIM,
        max_size=DIM,
    ).filter(lambda v: any(abs(x) > 1e-6 for x in v))


@given(_nonzero_vector())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_cosine_idempotent(v: list[float]) -> None:
    """cosine(a, a) == 1.0 for any non-zero vector."""
    assert _cosine(v, v) == pytest.approx(1.0, abs=1e-6)


@given(_nonzero_vector(), _nonzero_vector())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_cosine_symmetric(a: list[float], b: list[float]) -> None:
    """cosine(a, b) == cosine(b, a) for any non-zero pair."""
    assert _cosine(a, b) == pytest.approx(_cosine(b, a), abs=1e-12)


@given(_nonzero_vector(), _nonzero_vector())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_cosine_bounded(a: list[float], b: list[float]) -> None:
    """Cosine output is always in [-1.0, 1.0]."""
    cos = _cosine(a, b)
    assert -1.0 - COS_TOL <= cos <= 1.0 + COS_TOL


@given(_nonzero_vector(), _nonzero_vector(), _nonzero_vector())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_angular_distance_triangle_inequality(
    a: list[float], b: list[float], c: list[float]
) -> None:
    """Angular distance d(a,b) = arccos(cos(a,b)) satisfies the triangle inequality.

    This is a real property of the metric (unlike the original benchmark
    which compared three independent random scalars and reported a
    spurious ~50% pass rate).
    """
    d_ab = _angular_distance(a, b)
    d_bc = _angular_distance(b, c)
    d_ac = _angular_distance(a, c)
    assert d_ac <= d_ab + d_bc + 1e-9


# Top-level imports above ensure hypothesis examples don't pay the
# heavy first-call import cost (which exceeded the default 200ms deadline).
_ZONE_ORDER = [
    GalacticZone.CORE,
    GalacticZone.INNER_RIM,
    GalacticZone.MID_BAND,
    GalacticZone.OUTER_RIM,
    GalacticZone.FAR_EDGE,
]


@given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
@settings(max_examples=100, deadline=None)
def test_galactic_zone_classification_returns_valid_zone(distance: float) -> None:
    """classify_zone always returns a documented GalacticZone for d in [0, 1]."""
    zone = classify_zone(distance)
    assert isinstance(zone, GalacticZone)


@given(
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(max_examples=200, deadline=None)
def test_galactic_zone_classification_monotonic(d1: float, d2: float) -> None:
    """If d1 <= d2 then classify_zone(d1) is <= classify_zone(d2) by zone ordering.

    Zone ordering: CORE < INNER_RIM < MID_BAND < OUTER_RIM < FAR_EDGE.
    """
    z1 = classify_zone(d1)
    z2 = classify_zone(d2)
    if d1 <= d2:
        assert _ZONE_ORDER.index(z1) <= _ZONE_ORDER.index(z2)
    else:
        assert _ZONE_ORDER.index(z1) >= _ZONE_ORDER.index(z2)
