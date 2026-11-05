# -*- coding: utf-8 -*-

import os
import sys
import glob
import time
import collections
import pygame
try:
    import cv2
    import numpy as np
except Exception as ex:
    # 'cv2' is optional, the import may also fail with an 'OSError' when the
    # Python package is installed but one of its shared libraries is missing.
    cv2 = None
    OPENCV_ERROR = ex
else:
    OPENCV_ERROR = None
from PIL import Image
from pibooth.pictures import sizing
from pibooth import sounds
from pibooth.utils import PoolingTimer, LOGGER
from pibooth.language import get_translated_text
from pibooth.camera.base import BaseCamera


# On macOS the webcams are driven by AVFoundation: OpenCV always delivers the
# frames in the active format of the webcam, whatever size is asked (see
# 'setWidthHeight' in OpenCV 'cap_avfoundation_mac.mm'), so the frame size is
# never changed on this platform.
IS_MACOS = sys.platform == 'darwin'

# On Linux, the OpenCV port N is the device /dev/videoN
LINUX_VIDEO_DEVICES = '/sys/class/video4linux'


def _macos_camera_names():
    """Return the names of the webcams in the order of the OpenCV ports on
    macOS. OpenCV lists the video and muxed AVFoundation devices, sorted by
    their unique ID (see 'startCaptureDevice' in 'cap_avfoundation_mac.mm').
    Requires the optional 'pyobjc-framework-AVFoundation' package.
    """
    try:
        import AVFoundation as av  # pylint: disable=import-outside-toplevel,import-error,no-member
    except ImportError as ex:
        LOGGER.debug("Webcam names not available: %s", ex)
        return []
    devices = list(av.AVCaptureDevice.devicesWithMediaType_(av.AVMediaTypeVideo))  # pylint: disable=no-member
    devices += list(av.AVCaptureDevice.devicesWithMediaType_(av.AVMediaTypeMuxed))  # pylint: disable=no-member
    devices.sort(key=lambda device: str(device.uniqueID()))
    return [str(device.localizedName()).replace(u'\xa0', ' ') for device in devices]


def _linux_camera_names():
    """Return the names of the webcams in the order of the OpenCV ports on
    Linux (the port N is the device /dev/videoN, some of them having no name).
    """
    names = []
    for path in sorted(glob.glob(os.path.join(LINUX_VIDEO_DEVICES, 'video*')),
                       key=lambda path: int(path.rsplit('video', 1)[1])):
        port = int(path.rsplit('video', 1)[1])
        names.extend([''] * (port - len(names)))  # Missing ports have no name
        try:
            with open(os.path.join(path, 'name'), encoding='utf-8') as fp:
                names.append(fp.read().strip())
        except OSError:
            names.append('')
    return names


def get_cv_camera_names():
    """Return the names of the webcams seen by OpenCV, the index in the
    list being the OpenCV port. Return an empty list if the names can not be
    retrieved on this platform.
    """
    if IS_MACOS:
        return _macos_camera_names()
    if sys.platform.startswith('linux'):
        return _linux_camera_names()
    return []


def _find_port_by_name(name):
    """Return the OpenCV port of the first webcam whose name contains the
    given text (case insensitive), or None if not found.
    """
    names = get_cv_camera_names()
    for port, camera_name in enumerate(names):
        if name.lower() in camera_name.lower():
            return port
    LOGGER.warning("No webcam named '%s' among %s", name, names or "the webcams (names not available)")
    return None


# After a webcam is opened, macOS (AVFoundation) delivers no frame for a few
# seconds while the camera starts: reading is retried during this delay.
WARMUP_TIMEOUT = 8  # seconds


def _open_port(port):
    """Open the given OpenCV port and return the camera proxy, or None if
    no camera answers on it.
    """
    if IS_MACOS:
        # Force the native backend: the FFMPEG one is tried first by default
        # and logs an error for every port it can not list
        camera = cv2.VideoCapture(port, cv2.CAP_AVFOUNDATION)
    else:
        camera = cv2.VideoCapture(port)
    if camera.isOpened():
        return camera
    camera.release()
    return None


def _warmup(camera, timeout=None):
    """Read frames until the camera delivers a valid one, or the timeout is
    reached. Return True if a frame was obtained.

    A freshly opened webcam (especially on macOS, or after another application
    released it) reports itself as opened but delivers no frame for a few
    seconds. Without this wait, the first preview read fails and pibooth would
    fall in its failsafe state.
    """
    if timeout is None:
        timeout = WARMUP_TIMEOUT
    start = time.time()
    while time.time() - start < timeout:
        ret, _ = camera.read()
        if ret:
            LOGGER.debug("Webcam ready after %.1fs", time.time() - start)
            return True
        time.sleep(0.2)
    LOGGER.warning("Webcam still delivers no frame after %ss", timeout)
    return False


def get_cv_camera_proxy(port=None):
    """Return camera proxy if an OpenCV compatible camera is found
    else return None.

    :param port: look on given port number, or on the first webcam whose name
                 contains the given text (None to test the 3 first ports)
    :type port: int or str
    """
    if not cv2:
        # OpenCV is not installed or can not be loaded
        LOGGER.debug("OpenCV not available: %s", OPENCV_ERROR)
        return None

    names = get_cv_camera_names()
    if names:
        LOGGER.info("Webcams seen by OpenCV: %s",
                    ", ".join("{} = '{}'".format(i, name) for i, name in enumerate(names)))

    if isinstance(port, str):
        port = _find_port_by_name(port)
        if port is None:
            return None
        ports = [port]
    elif port is not None:
        if not isinstance(port, int):
            raise TypeError("Invalid OpenCV camera port '{}'".format(type(port)))
        ports = [port]
    else:
        ports = range(3)  # Test 3 first ports

    for i in ports:
        camera = _open_port(i)
        if camera:
            LOGGER.info("Using OpenCV camera on port %s%s", i, " ('{}')".format(names[i]) if i < len(names) else "")
            return camera

    if IS_MACOS:
        LOGGER.warning("No webcam found: check that the camera access is granted to the terminal "
                       "application in 'System Settings > Privacy & Security > Camera' (macOS asks "
                       "for it at the first start, pibooth may have to be started again)")
    return None


class CvCamera(BaseCamera):

    """OpenCV camera management.
    """

    IMAGE_EFFECTS = [u'none',
                     u'blur',
                     u'contour',
                     u'detail',
                     u'edge_enhance',
                     u'edge_enhance_more',
                     u'emboss',
                     u'find_edges',
                     u'smooth',
                     u'smooth_more',
                     u'sharpen']

    # Captures are taken from the preview stream: the sharpest frame of the
    # last SMILE_DELAY seconds (while "Smile" is displayed), the preview keeps
    # running instead of freezing for a separate capture.
    SMILE_DELAY = 0.5
    STREAM_WINDOW = 0.3

    def __init__(self, camera_proxy):
        super(CvCamera, self).__init__(camera_proxy)
        self._overlay_alpha = 255
        self._preview_resolution = None
        self._recent = collections.deque(maxlen=12)       # (time, full size BGR frame)
        self._clip_buffer = collections.deque()            # (time, small BGR frame)

    def _specific_initialization(self):
        """Camera initialization.
        """
        _warmup(self._cam)
        self._preview_resolution = self._get_frame_size()
        LOGGER.debug("Preview resolution is %s", self._preview_resolution)
        if not self._cam.set(cv2.CAP_PROP_ISO_SPEED, self.preview_iso):
            LOGGER.debug("Camera does not support ISO setting, ignored")

    def _get_frame_size(self):
        """Return the (width, height) of the frames delivered by the camera.
        """
        return (int(self._cam.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self._cam.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    def _set_frame_size(self, size):
        """Ask the camera for the given (width, height) of frames and return the
        size really applied: a webcam only supports a few sizes and the driver
        picks the nearest one.
        """
        if IS_MACOS:
            LOGGER.debug("Frame size can not be changed on macOS, keeping %s", self._get_frame_size())
            return self._get_frame_size()
        self._cam.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
        self._cam.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
        applied = self._get_frame_size()
        if applied != tuple(int(v) for v in size):
            LOGGER.debug("Camera does not support frame size %s, using %s", tuple(size), applied)
        return applied

    def _show_overlay(self, text, alpha):
        """Add an image as an overlay.
        """
        if self._window:  # No window means no preview displayed
            rect = self.get_rect()
            self._overlay_alpha = alpha
            pil_image = self.build_overlay((rect.width, rect.height), str(text), 255)
            # Remove alpha from overlay
            self._overlay = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2RGB)

    def _rotate_image(self, image, rotation):
        """Rotate an OpenCV image, clockwise.
        """
        if rotation == 90:
            image = cv2.transpose(image)
            return cv2.flip(image, 1)
        elif rotation == 180:
            return cv2.flip(image, -1)
        elif rotation == 270:
            image = cv2.transpose(image)
            return cv2.flip(image, 0)
        return image

    def _read_frame(self):
        """Return a frame from the webcam. A webcam may stop delivering frames
        for a short while (another application using it, the system switching
        the camera, ...): the read is retried during a few seconds before
        giving up so a transient glitch does not crash the capture sequence.
        """
        ret, image = self._cam.read()
        if not ret:
            LOGGER.warning("No frame delivered by the webcam, waiting for it to recover")
            if _warmup(self._cam):
                ret, image = self._cam.read()
        return ret, image

    def _get_preview_image(self):
        """Capture a new preview image.
        """
        rect = self.get_rect()

        ret, image = self._read_frame()
        if not ret:
            raise IOError("Can not get camera preview image")
        self._remember_frame(image)
        image = self._rotate_image(image, self.preview_rotation)

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Crop to keep aspect ratio of the resolution
        height, width = image.shape[:2]
        cropped = sizing.new_size_by_croping_ratio((width, height), self.resolution)
        image = image[cropped[1]:cropped[3], cropped[0]:cropped[2]]
        # Resize to fit the available space in the window
        height, width = image.shape[:2]
        size = sizing.new_size_keep_aspect_ratio((width, height), (rect.width, rect.height), 'outer')
        image = cv2.resize(image, size, interpolation=cv2.INTER_AREA)

        if self.preview_flip:
            image = cv2.flip(image, 1)

        if self._overlay is not None:
            if self._overlay.shape != image.shape:
                # Previous operations may create a size with one pixel gap
                self._overlay = cv2.resize(self._overlay, (image.shape[1], image.shape[0]))
            image = cv2.addWeighted(image, 1, self._overlay, self._overlay_alpha / 255., 0)
        return Image.fromarray(image)

    def _remember_frame(self, frame):
        """Keep the recent preview frames (stream capture) and a small copy for
        the video clip (at most 'clip_fps' per second, last 'clip_seconds').
        """
        now = time.monotonic()
        self._recent.append((now, frame))
        if self.clip_seconds <= 0:
            return
        # 10% tolerance: a 30 fps camera gives exactly 15 fps (every other frame)
        if self._clip_buffer and now - self._clip_buffer[-1][0] < 0.9 / self.clip_fps:
            return
        height, width = frame.shape[:2]
        size = (self.clip_width, int(height * self.clip_width / width) // 2 * 2)  # Even size for H.264
        small = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        small = self._rotate_image(small, self.capture_rotation)
        if self.capture_flip:
            small = cv2.flip(small, 1)
        self._clip_buffer.append((now, small))
        while now - self._clip_buffer[0][0] > self.clip_seconds:
            self._clip_buffer.popleft()

    def drop_clip(self):
        super(CvCamera, self).drop_clip()
        self._clip_buffer.clear()

    def _stream_frame(self):
        """Return the sharpest preview frame of the last STREAM_WINDOW seconds,
        or None if the preview stream is not running.
        """
        now = time.monotonic()
        frames = [frame for stamp, frame in self._recent if now - stamp <= self.STREAM_WINDOW]
        if not frames:
            return None

        def sharpness(frame):
            gray = cv2.cvtColor(cv2.resize(frame, (480, 270)), cv2.COLOR_BGR2GRAY)
            return cv2.Laplacian(gray, cv2.CV_64F).var()
        return max(frames, key=sharpness)

    def _post_process_capture(self, capture_data):
        """Rework capture data.

        :param capture_data: couple (frame, effect)
        :type capture_data: tuple
        """
        frame, effect = capture_data

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Crop to keep aspect ratio of the resolution
        height, width = image.shape[:2]
        cropped = sizing.new_size_by_croping_ratio((width, height), self.resolution)
        image = image[cropped[1]:cropped[3], cropped[0]:cropped[2]]
        # Resize to fit the resolution
        height, width = image.shape[:2]
        size = sizing.new_size_keep_aspect_ratio((width, height), self.resolution, 'outer')
        image = cv2.resize(image, size, interpolation=cv2.INTER_AREA)

        if self.capture_flip:
            image = cv2.flip(image, 1)

        if effect != 'none':
            LOGGER.warning("Effect with OpenCV camera is not implemented")

        # Ensure contiguous uint8 array and explicit RGB for PIL (avoids black image on some setups)
        image = np.ascontiguousarray(image, dtype=np.uint8)
        return Image.fromarray(image, mode='RGB')

    def preview(self, window, flip=True):
        """Setup the preview.
        """
        self._window = window
        self.preview_flip = flip
        self._window.show_image(self._get_preview_image())

    def preview_countdown(self, timeout, alpha=80):
        """Show a countdown of `timeout` seconds on the preview.
        Returns when the countdown is finished.
        """
        timeout = int(timeout)
        if timeout < 1:
            raise ValueError("Start time shall be greater than 0")

        timer = PoolingTimer(timeout)
        while not timer.is_timeout():
            remaining = int(timer.remaining() + 1)
            if self._overlay is None or remaining != timeout:
                # Rebluid overlay only if remaining number has changed
                self._show_overlay(str(remaining), alpha)
                sounds.countdown(remaining)
                timeout = remaining

            updated_rect = self._window.show_image(self._get_preview_image())
            pygame.event.pump()
            if updated_rect:
                pygame.display.update(updated_rect)

        self._show_smile(alpha)

    def _show_smile(self, alpha):
        """Display "Smile" on the running preview during SMILE_DELAY seconds,
        the capture is then taken from these frames.
        """
        self._show_overlay(get_translated_text('smile'), alpha)
        timer = PoolingTimer(self.SMILE_DELAY)
        while True:
            updated_rect = self._window.show_image(self._get_preview_image())
            pygame.event.pump()
            if updated_rect:
                pygame.display.update(updated_rect)
            if timer.is_timeout():
                break

    def preview_wait(self, timeout, alpha=80):
        """Wait the given time.
        """
        timeout = int(timeout)
        if timeout < 1:
            raise ValueError("Start time shall be greater than 0")

        timer = PoolingTimer(timeout)
        while not timer.is_timeout():
            updated_rect = self._window.show_image(self._get_preview_image())
            pygame.event.pump()
            if updated_rect:
                pygame.display.update(updated_rect)

        self._show_smile(alpha)

    def stop_preview(self):
        """Stop the preview.
        """
        self._hide_overlay()
        self._window = None

    def capture(self, effect=None):
        """Capture a new picture.
        """
        effect = str(effect).lower()
        if effect not in self.IMAGE_EFFECTS:
            raise ValueError("Invalid capture effect '{}' (choose among {})".format(effect, self.IMAGE_EFFECTS))

        # The clip segment of this capture: the frames recorded before it
        self._clip.extend(frame for _, frame in self._clip_buffer)
        self._clip_buffer.clear()

        # Take the capture from the running preview stream when it has the
        # wanted size (no freeze, no re-negotiation with the webcam)
        frame = self._stream_frame() if self._preview_resolution == tuple(self.resolution) else None
        self._recent.clear()
        if frame is not None and self.capture_iso == self.preview_iso:
            LOGGER.debug("Taking capture from the preview stream at resolution %s", self._preview_resolution)
            self._captures.append((self._rotate_image(frame, self.capture_rotation), effect))
            self._hide_overlay()
            return

        capture_size = self._set_frame_size(self.resolution)

        if self.capture_iso != self.preview_iso:
            self._cam.set(cv2.CAP_PROP_ISO_SPEED, self.capture_iso)

        # Minimal delay + flush so first frame is valid (avoids black frame, keeps latency low)
        time.sleep(0.15)
        for _ in range(4):
            self._cam.read()

        LOGGER.debug("Taking capture at resolution %s", capture_size)
        ret, image = self._read_frame()
        if not ret and capture_size != self._preview_resolution:
            # Some webcams stop delivering frames after a size change
            LOGGER.warning("Camera can not capture at resolution %s, using the preview one", capture_size)
            self._set_frame_size(self._preview_resolution)
            ret, image = self._read_frame()
        if not ret:
            raise IOError("Can not capture frame")
        image = self._rotate_image(image, self.capture_rotation)

        if self._get_frame_size() != self._preview_resolution:
            LOGGER.debug("Putting preview resolution back to %s", self._preview_resolution)
            self._set_frame_size(self._preview_resolution)

        if self.capture_iso != self.preview_iso:
            self._cam.set(cv2.CAP_PROP_ISO_SPEED, self.preview_iso)

        self._captures.append((image, effect))
        time.sleep(0.2)  # Brief pause so "Smile" is visible

        self._hide_overlay()  # If stop_preview() has not been called

    def quit(self):
        """Close the camera driver, it's definitive.
        """
        if self._cam:
            self._cam.release()
