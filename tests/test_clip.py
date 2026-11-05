# -*- coding: utf-8 -*-

"""Tests of the capture from the preview stream, of the video clip recording
(OpenCV camera) and of the clip plugin (H.264 MP4 with the theme watermark)."""

import sys
import time
import os.path as osp
import numpy as np
import pytest

from pibooth import theme
from pibooth.camera import opencv
from pibooth.camera.opencv import CvCamera, get_cv_camera_proxy

cv2 = pytest.importorskip("cv2")
sys.path.insert(0, osp.join(osp.dirname(osp.dirname(osp.abspath(__file__))), 'plugins'))
import pibooth_clip as clip  # noqa: E402
import pibooth_r2_upload as r2  # noqa: E402
from test_camera_opencv import fake_cv2  # noqa: E402,F401  pylint: disable=unused-import


class Clock(object):
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(opencv.time, 'monotonic', clock)
    return clock


@pytest.fixture
def camera(fake_cv2, monkeypatch):  # noqa: F811  pylint: disable=redefined-outer-name
    monkeypatch.setattr(opencv, 'IS_MACOS', True)
    cam = CvCamera(get_cv_camera_proxy())
    cam.initialize(100, (1280, 720))
    cam._cam.set_calls.clear()  # pylint: disable=protected-access
    return cam


def frame(value, sharp=False):
    image = np.full((720, 1280, 3), value, np.uint8)
    if sharp:
        image[::2, :, :] = 255 - value  # Strong edges
    return image


def test_capture_is_the_sharpest_recent_stream_frame(camera, clock):
    camera._remember_frame(frame(10))  # pylint: disable=protected-access
    clock.now += 0.1
    camera._remember_frame(frame(20, sharp=True))  # pylint: disable=protected-access
    clock.now += 0.1
    camera._remember_frame(frame(30))  # pylint: disable=protected-access
    camera.capture()
    captured = np.asarray(camera.get_captures()[0])
    assert {captured[0, 0, 0], captured[1, 0, 0]} == {235, 20}
    # No frame size change and no extra read: the stream was used as is
    assert not camera._cam.set_calls  # pylint: disable=protected-access


def test_capture_without_recent_stream_frame_reads_the_camera(camera, clock):
    camera._remember_frame(frame(10, sharp=True))  # pylint: disable=protected-access
    clock.now += 5  # Too old
    camera.capture()
    assert np.asarray(camera.get_captures()[0])[0, 0, 0] == 120  # FakeVideoCapture frame


def test_clip_keeps_the_last_seconds_before_each_capture(camera, clock):
    camera.clip_seconds, camera.clip_fps, camera.clip_width = 1.5, 10, 480
    for _ in range(2):              # Two captures of the sequence
        for i in range(60):         # 3 seconds of preview at 20 fps
            camera._remember_frame(frame(i))  # pylint: disable=protected-access
            clock.now += 0.05
        camera.capture()
    frames = camera.get_clip()
    # 1.5 s at 10 fps per capture (+1 for the boundary frame)
    assert 2 * 15 <= len(frames) <= 2 * 16
    assert frames[0].shape == (270, 480, 3)
    assert camera.get_clip() == []  # Dropped once read


def test_clip_disabled_by_default(camera):
    camera._remember_frame(frame(10))  # pylint: disable=protected-access
    camera.capture()
    assert camera.get_clip() == []


@pytest.fixture
def droidknights():
    previous = theme.CURRENT
    theme.CURRENT = theme.load('droidknights')
    yield theme.CURRENT
    theme.CURRENT = previous


def read_video(path):
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ret, image = cap.read()
        if not ret:
            break
        frames.append(image)
    cap.release()
    return frames


def test_write_clip_with_watermark(tmp_path, droidknights):
    frames = [np.full((270, 480, 3), 30, np.uint8) for _ in range(15)]
    path = str(tmp_path / 'clip.mp4')
    watermark = clip.get_watermark()
    assert watermark and watermark[1] == 'bottomright'
    clip.write_clip(path, frames, 15, watermark)

    with open(path, 'rb') as fp:
        data = fp.read()
    assert b'avc1' in data  # H.264, playable in the browsers and on the phones
    video = read_video(path)
    assert len(video) == 15 and video[0].shape == (270, 480, 3)
    # The watermark is in the bottom right corner only
    corner = video[0][200:265, 370:475].astype(int)
    assert np.abs(corner - 30).max() > 60
    assert np.abs(video[0][10:60, 10:100].astype(int) - 30).max() < 15


def test_no_watermark_without_theme_logo():
    previous = theme.CURRENT
    theme.CURRENT = theme.load('classic')
    try:
        assert clip.get_watermark() is None
    finally:
        theme.CURRENT = previous


class Camera(object):
    def __init__(self, frames):
        self.frames = frames

    def get_clip(self):
        frames, self.frames = self.frames, []
        return frames


class Cfg(object):
    def getint(self, section, option):
        return 15


class App(object):
    pass


def test_plugin_saves_the_clip_next_to_the_picture(tmp_path, droidknights):
    app = App()
    app.previous_picture_file = str(tmp_path / '2026-10-16_pibooth.jpg')
    app.camera = Camera([np.full((270, 480, 3), 50, np.uint8)] * 10)
    clip.state_processing_exit(Cfg(), app)
    assert app.previous_clip_file == str(tmp_path / '2026-10-16_pibooth.mp4')
    assert len(read_video(app.previous_clip_file)) == 10


def test_plugin_without_frames_saves_nothing(tmp_path):
    app = App()
    app.previous_picture_file = str(tmp_path / 'p.jpg')
    app.camera = Camera([])
    clip.state_processing_exit(Cfg(), app)
    assert app.previous_clip_file is None


def test_r2_uploads_the_clip_with_the_picture_key(tmp_path, monkeypatch):
    calls = []

    class S3(object):
        def upload_file(self, path, bucket, key, ExtraArgs=None):  # noqa: N803
            calls.append((osp.basename(path), key, ExtraArgs['ContentType']))

    uploader = r2.R2Uploader("https://e", "b", "k", "s", public_url="https://pics", client=S3())
    monkeypatch.setattr(r2, "_UPLOADER", uploader)
    monkeypatch.setattr(r2, "_THREADS", [])
    picture, video = tmp_path / 'p.jpg', tmp_path / 'p.mp4'
    picture.write_bytes(b'jpeg')
    video.write_bytes(b'mp4')
    app = App()
    app.previous_picture_file, app.previous_clip_file = str(picture), str(video)
    r2.state_processing_exit(app)
    for thread in r2._THREADS:  # pylint: disable=protected-access
        thread.join(2)
    key = app.previous_picture_key
    assert calls == [('p.jpg', key, 'image/jpeg'), ('p.mp4', key[:-4] + '.mp4', 'video/mp4')]
    time.sleep(0)


def test_longer_clip_for_a_single_capture():
    class ClipCfg(object):
        def getboolean(self, section, option):
            return True

        def getfloat(self, section, option):
            return {'seconds': 1.5, 'single_seconds': 5.0}[option]

    app = App()
    app.camera = Camera([])
    app.capture_nbr = 1
    clip.state_preview_enter(ClipCfg(), app)
    assert app.camera.clip_seconds == 5.0
    app.capture_nbr = 4
    clip.state_preview_enter(ClipCfg(), app)
    assert app.camera.clip_seconds == 1.5
