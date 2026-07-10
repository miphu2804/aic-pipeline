import numpy as np
import pytest

from keyframe_extraction import cadre


# --- frame_signature --------------------------------------------------------
def test_frame_signature_shape_is_grid_squared_times_three():
    rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    assert cadre.frame_signature(rgb, grid=4).shape == (4 * 4 * 3,)


def test_frame_signature_is_normalised_to_unit_range():
    rgb = np.full((16, 16, 3), 255, dtype=np.uint8)
    sig = cadre.frame_signature(rgb, grid=2)
    assert np.allclose(sig, 1.0)


def test_frame_signature_distinguishes_left_right_halves():
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    rgb[:, 4:, 0] = 255  # right half is red
    sig = cadre.frame_signature(rgb, grid=2).reshape(2, 2, 3)
    assert sig[0, 0, 0] == pytest.approx(0.0)  # top-left block: no red
    assert sig[0, 1, 0] == pytest.approx(1.0)  # top-right block: full red


# --- pairwise_distances -----------------------------------------------------
def test_pairwise_distances_is_zero_on_the_diagonal():
    sig = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    d = cadre.pairwise_distances(sig)
    assert np.allclose(np.diag(d), 0.0)


def test_pairwise_distances_matches_euclidean():
    sig = np.array([[0.0, 0.0], [3.0, 4.0]])
    d = cadre.pairwise_distances(sig)
    assert d[0, 1] == pytest.approx(5.0)


# --- facility_location ------------------------------------------------------
def test_facility_location_picks_one_per_cluster():
    # three tight clusters far apart; k=3 should land one medoid in each.
    pts = np.array([[0.0], [0.1], [10.0], [10.1], [20.0], [20.1]])
    d = cadre.pairwise_distances(pts)
    chosen = cadre.facility_location(d, k=3)
    clusters = {idx // 2 for idx in chosen}
    assert clusters == {0, 1, 2}


def test_facility_location_returns_k_distinct_indices():
    rng = np.random.RandomState(0)
    d = cadre.pairwise_distances(rng.rand(20, 3))
    chosen = cadre.facility_location(d, k=5)
    assert len(chosen) == 5
    assert len(set(chosen)) == 5


# --- local_search -----------------------------------------------------------
def test_local_search_never_worsens_representativeness():
    rng = np.random.RandomState(1)
    d = cadre.pairwise_distances(rng.rand(30, 4))
    start = [0, 1, 2]

    def cost(sel):
        return d[:, sel].min(axis=1).mean()

    refined = cadre.local_search(d, start, rounds=5)
    assert cost(refined) <= cost(start) + 1e-9


def test_local_search_keeps_the_same_number_of_keyframes():
    rng = np.random.RandomState(2)
    d = cadre.pairwise_distances(rng.rand(25, 3))
    refined = cadre.local_search(d, [0, 5, 10], rounds=3)
    assert len(refined) == 3
    assert len(set(refined)) == 3


# --- select_keyframes -------------------------------------------------------
def test_select_keyframes_count_is_ceil_ratio_times_n():
    sig = np.random.RandomState(3).rand(100, 12)
    assert len(cadre.select_keyframes(sig, ratio=0.03)) == 3  # ceil(0.03 * 100)


def test_select_keyframes_returns_sorted_unique_indices():
    sig = np.random.RandomState(4).rand(50, 12)
    out = cadre.select_keyframes(sig, ratio=0.1)
    assert out == sorted(out)
    assert len(out) == len(set(out))


def test_select_keyframes_covers_both_halves_of_a_two_scene_clip():
    # first 25 frames are one colour, next 25 another; k=2 must cover both scenes.
    sig = np.vstack([np.tile([0.0] * 3, (25, 1)), np.tile([1.0] * 3, (25, 1))])
    out = cadre.select_keyframes(sig, ratio=0.04)  # ceil(0.04*50)=2
    assert any(i < 25 for i in out)
    assert any(i >= 25 for i in out)


def test_select_keyframes_handles_tiny_input():
    assert cadre.select_keyframes(np.zeros((1, 12)), ratio=0.03) == [0]
    assert cadre.select_keyframes(np.zeros((0, 12)), ratio=0.03) == []


def test_select_keyframes_rejects_out_of_range_ratio():
    sig = np.zeros((10, 12))
    with pytest.raises(ValueError):
        cadre.select_keyframes(sig, ratio=0.0)
    with pytest.raises(ValueError):
        cadre.select_keyframes(sig, ratio=1.5)


# --- arc_length_seed (DACS) -------------------------------------------------
def _half_static_half_dynamic(n_static=50, n_dynamic=50, dims=3):
    """A clip whose first half is frozen and second half changes every frame."""
    static = np.zeros((n_static, dims))
    ramp = np.linspace(0.2, 1.0, n_dynamic)[:, None] * np.ones((1, dims))
    return np.vstack([static, ramp])


def test_arc_length_seed_returns_sorted_unique_within_budget():
    sig = np.random.RandomState(5).rand(60, 12)
    seeds = cadre.arc_length_seed(sig, k=5)
    assert seeds == sorted(seeds)
    assert len(seeds) == len(set(seeds))
    assert len(seeds) <= 5


def test_arc_length_seed_puts_more_keyframes_where_content_moves():
    # equal-sized static/dynamic halves: a plain uniform split would give 2/2, but
    # DACS follows visual change and concentrates keyframes in the moving half.
    sig = _half_static_half_dynamic()
    seeds = cadre.arc_length_seed(sig, k=4)
    in_dynamic = sum(i >= 50 for i in seeds)
    in_static = sum(i < 50 for i in seeds)
    assert in_dynamic > in_static


def test_arc_length_seed_static_clip_falls_back_to_uniform_spacing():
    # No visual change ⇒ arc length is zero ⇒ evenly spaced temporal samples.
    seeds = cadre.arc_length_seed(np.zeros((40, 6)), k=4)
    assert len(seeds) == 4
    assert seeds == sorted(seeds)
    # evenly spaced: consecutive keyframes are a constant stride apart
    assert len(set(np.diff(seeds))) == 1


def test_arc_length_seed_handles_tiny_and_degenerate_input():
    assert cadre.arc_length_seed(np.zeros((0, 6)), k=3) == []
    assert cadre.arc_length_seed(np.zeros((5, 6)), k=1) == [0]


# --- select_keyframes_dacs --------------------------------------------------
def test_select_keyframes_dacs_count_within_budget():
    sig = np.random.RandomState(6).rand(100, 12)
    out = cadre.select_keyframes_dacs(sig, ratio=0.05)  # ceil(0.05*100)=5
    assert 1 <= len(out) <= 5
    assert out == sorted(out)
    assert len(out) == len(set(out))


def test_select_keyframes_dacs_covers_both_scenes():
    sig = np.vstack([np.tile([0.0] * 3, (25, 1)), np.tile([1.0] * 3, (25, 1))])
    out = cadre.select_keyframes_dacs(sig, ratio=0.04)  # k=2
    assert any(i < 25 for i in out)
    assert any(i >= 25 for i in out)


def test_select_keyframes_dacs_refine_matches_budget_and_covers_scenes():
    sig = np.vstack([np.tile([0.0] * 3, (25, 1)), np.tile([1.0] * 3, (25, 1))])
    out = cadre.select_keyframes_dacs(sig, ratio=0.04, refine=True)
    assert any(i < 25 for i in out)
    assert any(i >= 25 for i in out)


def test_select_keyframes_dacs_handles_tiny_input_and_bad_ratio():
    assert cadre.select_keyframes_dacs(np.zeros((1, 12))) == [0]
    assert cadre.select_keyframes_dacs(np.zeros((0, 12))) == []
    with pytest.raises(ValueError):
        cadre.select_keyframes_dacs(np.zeros((10, 12)), ratio=0.0)
