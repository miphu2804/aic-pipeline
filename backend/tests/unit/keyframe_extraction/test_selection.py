import pytest

from keyframe_extraction.dake import compute_frame_steepness, select_keyframes


class TestComputeFrameSteepness:
    def test_empty_input(self):
        assert compute_frame_steepness([]) == []

    def test_single_frame(self):
        assert compute_frame_steepness([1000]) == []

    def test_flat_region_has_zero_steepness(self):
        scored = compute_frame_steepness([1000, 1000, 1000, 1000])
        for _, steepness in scored:
            assert steepness == pytest.approx(0.0)

    def test_sharp_jump_has_high_steepness(self):
        sizes = [1000, 1000, 1000, 5000, 5000, 5000]
        scored = compute_frame_steepness(sizes)
        steepness_by_idx = dict(scored)
        assert steepness_by_idx[2] > steepness_by_idx[0]

    def test_returns_n_minus_1_entries(self):
        sizes = [100, 200, 300, 400, 500]
        scored = compute_frame_steepness(sizes)
        assert len(scored) == len(sizes) - 1

    def test_window_limits_neighbors(self):
        """Forward window should be at most 3 frames by default."""
        sizes = [1000, 2000, 3000, 4000, 5000, 6000]
        scored = compute_frame_steepness(sizes, window=3)
        assert len(scored) == 5


class TestSelectKeyframes:
    def test_empty_input(self):
        assert select_keyframes([], rho=0.5) == []

    def test_returns_at_least_one_frame(self):
        result = select_keyframes([1000, 1000, 1000], rho=0.01)
        assert len(result) >= 1

    def test_rho_controls_number_selected(self):
        sizes = list(range(100, 200))
        result_small = select_keyframes(sizes, rho=0.02)
        result_large = select_keyframes(sizes, rho=0.10)
        assert len(result_large) > len(result_small)

    def test_selects_frames_near_scene_change(self):
        sizes = [1000] * 50 + [5000] * 50
        result = select_keyframes(sizes, rho=0.05)
        boundary_frames = [i for i in result if 47 <= i <= 52]
        assert len(boundary_frames) >= 1

    def test_result_is_sorted_by_frame_order(self):
        sizes = [1000, 5000, 1000, 5000, 1000]
        result = select_keyframes(sizes, rho=0.5)
        assert result == sorted(result)

    def test_no_cascade_on_decreasing_sizes(self):
        """Monotonically decreasing sizes (I-frame artifact) should NOT
        produce a cluster of consecutive frames at the start."""
        sizes = [7000, 5500, 4800, 4400, 4200, 3900, 3600, 3400, 3200, 3100]
        sizes += [3000] * 90
        result = select_keyframes(sizes, rho=0.02)
        consecutive_start = sum(1 for i in result if i < 5)
        assert consecutive_start <= 2

    def test_warmup_excludes_early_frames(self):
        """With warmup, I-frame transient frames should be excluded."""
        sizes = [7000, 5500, 4800, 4400, 4200, 3900, 3600, 3400, 3200, 3100]
        sizes += [3000] * 40 + [6000] * 50
        result = select_keyframes(sizes, rho=0.05, warmup=10)
        assert all(i >= 10 for i in result)

    def test_warmup_zero_behaves_like_no_warmup(self):
        sizes = [1000, 5000, 1000, 5000, 1000]
        assert select_keyframes(sizes, rho=0.5, warmup=0) == select_keyframes(
            sizes, rho=0.5
        )

    def test_warmup_larger_than_video_returns_empty(self):
        sizes = [1000, 2000, 3000]
        result = select_keyframes(sizes, rho=0.5, warmup=100)
        assert result == []
