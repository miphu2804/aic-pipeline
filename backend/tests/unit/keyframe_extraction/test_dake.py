import math

import pytest

from keyframe_extraction.dake import calculate_steepness


def test_steepness_is_zero_when_sizes_are_equal():
    assert calculate_steepness(s_i=1000, s_j=1000, i=0, j=10, s_max=1000) == 0.0


def test_steepness_approaches_one_for_large_size_jump_over_short_distance():
    # delta = 100 * |2000-1000|/1000 = 100 -> S = 100/sqrt(1+100^2) ~= 0.99995
    result = calculate_steepness(s_i=1000, s_j=2000, i=0, j=1, s_max=1000)
    assert result == pytest.approx(0.99995, rel=1e-4)


def test_steepness_matches_known_value():
    # delta = 100*|1200-1000|/1000 = 20, d = 5 -> S = 20/sqrt(25+400)
    result = calculate_steepness(s_i=1000, s_j=1200, i=0, j=5, s_max=1000)
    expected = 20 / math.sqrt(25 + 400)
    assert result == pytest.approx(expected)


def test_steepness_when_frame_indices_are_equal_and_sizes_differ_is_one():
    # d=0, delta>0 -> S = delta/sqrt(0+delta^2) = 1.0
    result = calculate_steepness(s_i=1000, s_j=1200, i=3, j=3, s_max=1000)
    assert result == pytest.approx(1.0)


def test_steepness_raises_on_zero_s_max():
    with pytest.raises(ValueError):
        calculate_steepness(s_i=1000, s_j=1200, i=0, j=5, s_max=0)
