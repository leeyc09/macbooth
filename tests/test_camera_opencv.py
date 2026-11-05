# -*- coding: utf-8 -*-

"""Tests of the OpenCV camera without a real webcam: the OpenCV capture object
is replaced by a fake one delivering synthetic frames.
"""

import numpy as np
import pytest
from pibooth.camera import opencv
from pibooth.camera import find_camera
from pibooth.camera.opencv import CvCamera, get_cv_camera_proxy

cv2 = pytest.importorskip("cv2")


class FakeVideoCapture(object):

    """Mimic ``cv2.VideoCapture`` for a webcam supporting only 1280x720 and 1920x1080."""

    SUPPORTED = ((1280, 720), (1920, 1080))
    instances = []
    available_ports = (0,)

    def __init__(self, port, backend=None):
        self.port = port
        self.backend = backend
        self.size = (1280, 720)
        self.released = False
        self.set_calls = []
        FakeVideoCapture.instances.append(self)

    def isOpened(self):  # pylint: disable=invalid-name
        return self.port in self.available_ports

    def release(self):
        self.released = True

    def get(self, prop):
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self.size[0])
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self.size[1])
        return 0.0

    def set(self, prop, value):
        self.set_calls.append((prop, value))
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            self.size = (self._nearest(value, 0), self.size[1])
            return True
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            self.size = (self.size[0], self._nearest(value, 1))
            return True
        return False  # ISO and others are not supported

    def _nearest(self, value, index):
        return min((s[index] for s in self.SUPPORTED), key=lambda s: abs(s - value))

    def read(self):
        width, height = self.size
        return True, np.full((height, width, 3), 120, dtype=np.uint8)


@pytest.fixture
def fake_cv2(monkeypatch):
    FakeVideoCapture.instances = []
    FakeVideoCapture.available_ports = (0,)
    monkeypatch.setattr(opencv.cv2, 'VideoCapture', FakeVideoCapture)
    monkeypatch.setattr(opencv, 'get_cv_camera_names', lambda: [])
    monkeypatch.setattr(opencv, 'WARMUP_TIMEOUT', 0.3)  # Keep the tests fast
    return FakeVideoCapture


@pytest.fixture
def fake_names(monkeypatch):
    names = ['OBS Virtual Camera', 'MacBook Pro Camera', 'iPhone']
    monkeypatch.setattr(opencv, 'get_cv_camera_names', lambda: names)
    return names


@pytest.fixture
def no_other_camera(monkeypatch):
    import pibooth.camera as camera_module
    monkeypatch.setattr(camera_module, 'get_gp_camera_proxy', lambda: None)


def test_proxy_probes_the_first_ports(fake_cv2):
    fake_cv2.available_ports = (1,)
    proxy = get_cv_camera_proxy()
    assert proxy.port == 1
    # Port 0 failed and has been released
    assert fake_cv2.instances[0].port == 0 and fake_cv2.instances[0].released


def test_proxy_uses_the_given_port(fake_cv2):
    fake_cv2.available_ports = (0, 2)
    proxy = get_cv_camera_proxy(2)
    assert proxy.port == 2
    assert [cap.port for cap in fake_cv2.instances] == [2]


def test_proxy_returns_none_when_no_camera(fake_cv2):
    fake_cv2.available_ports = ()
    assert get_cv_camera_proxy() is None
    assert get_cv_camera_proxy(1) is None


def test_proxy_rejects_invalid_port(fake_cv2):
    with pytest.raises(TypeError):
        get_cv_camera_proxy(0.5)


def test_proxy_uses_the_camera_name(fake_cv2, fake_names):
    fake_cv2.available_ports = (0, 1, 2)
    assert get_cv_camera_proxy('macbook').port == 1
    assert get_cv_camera_proxy('iPhone').port == 2
    assert get_cv_camera_proxy('Canon') is None


def test_linux_camera_names(tmp_path, monkeypatch):
    # /dev/video0 and /dev/video2 exist, /dev/video1 does not
    for port, name in ((0, 'HD Webcam'), (2, 'Capture card')):
        (tmp_path / 'video{}'.format(port)).mkdir()
        (tmp_path / 'video{}'.format(port) / 'name').write_text(name + '\n')
    monkeypatch.setattr(opencv, 'LINUX_VIDEO_DEVICES', str(tmp_path))
    monkeypatch.setattr(opencv, 'IS_MACOS', False)
    monkeypatch.setattr(opencv.sys, 'platform', 'linux')
    assert opencv.get_cv_camera_names() == ['HD Webcam', '', 'Capture card']


def test_macos_camera_names_follow_opencv_order(monkeypatch):
    class Device(object):
        def __init__(self, name, uid):
            self._name, self._uid = name, uid

        def localizedName(self):  # pylint: disable=invalid-name
            return self._name

        def uniqueID(self):  # pylint: disable=invalid-name
            return self._uid

    class AVFoundation(object):
        AVMediaTypeVideo = 'vide'
        AVMediaTypeMuxed = 'muxx'

        class AVCaptureDevice(object):
            @staticmethod
            def devicesWithMediaType_(media_type):  # pylint: disable=invalid-name
                if media_type == 'vide':
                    return [Device(u'OBS Virtual Camera', '7626645E'), Device(u'MacBook\xa0Pro Camera', '6C707041')]
                return [Device(u'Capture card', 'FFFF')]

    monkeypatch.setitem(opencv.sys.modules, 'AVFoundation', AVFoundation)
    monkeypatch.setattr(opencv, 'IS_MACOS', True)
    # OpenCV sorts the devices by unique ID
    assert opencv.get_cv_camera_names() == ['MacBook Pro Camera', 'OBS Virtual Camera', 'Capture card']


def test_proxy_uses_avfoundation_on_macos(fake_cv2, monkeypatch):
    monkeypatch.setattr(opencv, 'IS_MACOS', True)
    proxy = get_cv_camera_proxy()
    assert proxy.backend == cv2.CAP_AVFOUNDATION
    monkeypatch.setattr(opencv, 'IS_MACOS', False)
    proxy = get_cv_camera_proxy()
    assert proxy.backend is None


def test_find_camera_forwards_the_port(fake_cv2, no_other_camera):
    fake_cv2.available_ports = (0, 1)
    cam = find_camera(cv_port=1)
    assert isinstance(cam, CvCamera)
    assert cam._cam.port == 1  # pylint: disable=protected-access


def test_capture_uses_the_nearest_supported_size(fake_cv2, monkeypatch):
    monkeypatch.setattr(opencv, 'IS_MACOS', False)
    cam = CvCamera(get_cv_camera_proxy())
    cam.initialize(100, (1934, 2464))
    cam.capture()
    captures = cam.get_captures()
    assert len(captures) == 1
    # Post-processing crops to the configured aspect ratio and resizes to the
    # resolution (the resize keeps the ratio, hence a possible 1-2 pixels gap)
    assert captures[0].size[0] == 1934 and abs(captures[0].size[1] - 2464) <= 2
    # The webcam was switched to its nearest size (1920x1080) then back to the preview one
    assert cam._cam.size == (1280, 720)  # pylint: disable=protected-access
    sizes = [v for p, v in cam._cam.set_calls if p == cv2.CAP_PROP_FRAME_WIDTH]  # pylint: disable=protected-access
    assert sizes == [1934, 1280]


def test_capture_keeps_the_native_size_on_macos(fake_cv2, monkeypatch):
    monkeypatch.setattr(opencv, 'IS_MACOS', True)
    cam = CvCamera(get_cv_camera_proxy())
    cam.initialize(100, (1280, 720))
    cam.capture()
    captures = cam.get_captures()
    assert captures[0].size == (1280, 720)
    frame_props = (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT)
    assert not [c for c in cam._cam.set_calls if c[0] in frame_props]  # pylint: disable=protected-access


def test_slow_camera_is_warmed_up_on_init(fake_cv2, monkeypatch):
    monkeypatch.setattr(opencv, 'IS_MACOS', False)
    proxy = get_cv_camera_proxy()
    # The webcam delivers nothing for its first few reads (macOS warmup)
    frames = {'count': 0}
    real_read = proxy.read

    def slow_read():
        frames['count'] += 1
        if frames['count'] < 2:
            return False, None
        return real_read()

    monkeypatch.setattr(proxy, 'read', slow_read)
    cam = CvCamera(proxy)
    cam.initialize(100, (1280, 720))  # _specific_initialization warms up
    assert frames['count'] >= 2  # Warmup consumed the empty read(s) before the first frame


def test_capture_falls_back_to_preview_size_when_frame_fails(fake_cv2, monkeypatch):
    monkeypatch.setattr(opencv, 'IS_MACOS', False)
    cam = CvCamera(get_cv_camera_proxy())
    cam.initialize(100, (1920, 1080))
    original_read = cam._cam.read  # pylint: disable=protected-access

    def read_fails_in_hd():
        if cam._cam.size == (1920, 1080):  # pylint: disable=protected-access
            return False, None
        return original_read()

    monkeypatch.setattr(cam._cam, 'read', read_fails_in_hd)  # pylint: disable=protected-access
    cam.capture()
    assert cam.get_captures()[0].size == (1920, 1080)


@pytest.mark.parametrize("value, expected", [("-1", None), ("0", 0), ("2", 2), ("", None), ("ask", "ask"), ("Ask", "ask"),
                                             ("iPhone", "iPhone"), ('"MacBook Pro"', "MacBook Pro")])
def test_plugin_reads_opencv_camera_option(value, expected):
    from pibooth.plugins.camera_plugin import CameraPlugin

    class Cfg(object):
        @staticmethod
        def get(section, key):
            assert (section, key) == ('CAMERA', 'opencv_camera')
            return value

    assert CameraPlugin._get_opencv_camera(Cfg()) == expected  # pylint: disable=protected-access
