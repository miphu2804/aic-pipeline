import av
import numpy as np

from keyframe_extraction.extractor import JpegSizeEncoder, KeyframeExtractor


def _blank_frame(width: int, height: int, fill: int) -> av.VideoFrame:
    frame = av.VideoFrame(width, height, "yuvj420p")
    for plane in frame.planes:
        plane.update(bytes([fill]) * plane.buffer_size)
    return frame


def _write_video(path, colors, width=32, height=32, fps=5) -> None:
    container = av.open(str(path), mode="w")
    stream = container.add_stream("mpeg4", rate=fps)
    stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
    for color in colors:
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:, :] = color
        for packet in stream.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
            container.mux(packet)
    for packet in stream.encode():  # flush
        container.mux(packet)
    container.close()


def test_measure_returns_positive_size_for_real_frame():
    encoder = JpegSizeEncoder(width=64, height=64, pix_fmt="yuvj420p")
    size = encoder.measure(_blank_frame(64, 64, fill=128), pts=0)
    assert size > 0


def test_extract_keyframes_cadre_covers_distinct_scenes(tmp_path):
    # three visually distinct colour scenes; CADRE should place its keyframes across
    # them rather than clustering in one.
    colors = [(200, 0, 0)] * 4 + [(0, 200, 0)] * 4 + [(0, 0, 200)] * 4
    path = tmp_path / "clip.mp4"
    _write_video(path, colors)

    extractor = KeyframeExtractor(cadre_ratio=0.25)  # ceil(0.25 * ~12) ≈ 3 keyframes
    keyframes = extractor.extract_keyframes_cadre(path)

    indices = [kf.frame_index for kf in keyframes]
    assert len(indices) >= 2
    assert indices == sorted(set(indices))  # sorted, unique
    assert max(indices) - min(indices) >= 4  # spread across the clip
    assert all(kf.timestamp_seconds >= 0 for kf in keyframes)


def test_extract_keyframes_dacs_covers_distinct_scenes(tmp_path):
    # DACS spreads keyframes across accumulated visual change; three distinct scenes
    # should be covered rather than clustered.
    colors = [(200, 0, 0)] * 4 + [(0, 200, 0)] * 4 + [(0, 0, 200)] * 4
    path = tmp_path / "clip.mp4"
    _write_video(path, colors)

    extractor = KeyframeExtractor(cadre_ratio=0.25)
    for refine in (False, True):
        keyframes = extractor.extract_keyframes_dacs(path, refine=refine)
        indices = [kf.frame_index for kf in keyframes]
        assert len(indices) >= 2
        assert indices == sorted(set(indices))  # sorted, unique
        assert max(indices) - min(indices) >= 4  # spread across the clip
        assert all(kf.timestamp_seconds >= 0 for kf in keyframes)
