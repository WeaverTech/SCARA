import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stiffness import E_STEEL, default_variants, evaluate, rod_stiffness  # noqa: E402


def _EI(d):
    return E_STEEL * math.pi * d ** 4 / 64.0


@pytest.mark.parametrize("ends,c_lat,c_tilt", [("pinned", 48.0, 12.0), ("clamped", 192.0, 16.0)])
def test_rod_matches_closed_form_for_short_carriage(ends, c_lat, c_tilt):
    d, L = 12.0, 350.0
    k_tilt, k_lat = rod_stiffness(d, L, h=0.5, ends=ends)
    assert k_lat == pytest.approx(c_lat * _EI(d) / L ** 3, rel=1e-3)
    assert k_tilt == pytest.approx(c_tilt * _EI(d) / L, rel=1e-2)


def test_longer_bushing_spacing_is_stiffer():
    k_short, _ = rod_stiffness(12.0, 350.0, 30.0, "clamped")
    k_long, _ = rod_stiffness(12.0, 350.0, 110.0, "clamped")
    assert k_long > k_short


def test_v2_recommended_is_much_stiffer_than_v1():
    rows = {v.name.split(":")[0]: evaluate(v, 3.57, 0.5, 1.0) for v in default_variants()}
    assert rows["v2c"]["k_tilt"] > 20 * rows["v1"]["k_tilt"]
    assert rows["v2c"]["k_tors"] > 100 * rows["v1"]["k_tors"]
    assert rows["v2c"]["sag_tip"] < 0.1
