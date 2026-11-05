# -*- coding: utf-8 -*-

"""Pibooth plugin to save a short video clip of the capture sequence.

The camera records the last ``seconds`` before each capture (OpenCV webcams
only); the segments are joined into an H.264 MP4 file saved next to the final
picture (``<picture name>.mp4``), with the watermark of the theme. The path is
stored in ``app.previous_clip_file`` so the R2 plugin uploads it with the
picture.

Enable the plugin with the ``[GENERAL][plugins]`` option. Options of the
``[CLIP]`` section: ``enabled``, ``seconds`` (per capture), ``single_seconds``
(the capture of a 1-capture sequence: longer, the clip would be too short
otherwise; limited by the duration of the preview countdown), ``fps``, ``width``.

The watermark is defined by the theme (``clip`` section of ``theme.json``)::

    "clip": {"watermark": "logo", "position": "bottomright", "width": 0.22, "opacity": 0.9}

where ``watermark`` is an asset name of the theme.
"""

import os.path as osp

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
from PIL import Image, ImageFilter

import pibooth
from pibooth import theme
from pibooth.utils import LOGGER

__version__ = "1.0.0"

SECTION = 'CLIP'
POSITIONS = ('topleft', 'topright', 'bottomleft', 'bottomright')


@pibooth.hookimpl
def pibooth_configure(cfg):
    """Declare the clip configuration options."""
    cfg.add_option(SECTION, 'enabled', True,
                   "Save (and upload) a video clip of the capture sequence",
                   "Video clip", ['True', 'False'])
    cfg.add_option(SECTION, 'seconds', 1.5,
                   "Seconds of video kept before each capture")
    cfg.add_option(SECTION, 'single_seconds', 5,
                   "Seconds of video kept before the capture of a 1-capture sequence "
                   "(at most the duration of the preview countdown)")
    cfg.add_option(SECTION, 'fps', 15,
                   "Frames per second of the video clip")
    cfg.add_option(SECTION, 'width', 480,
                   "Width in pixels of the video clip")


@pibooth.hookimpl
def pibooth_startup(cfg, app):
    """Ask the camera to record the clip frames."""
    if cv2 is None:
        LOGGER.warning("Video clip disabled: 'opencv-python' is not installed")
        return
    if cfg.getboolean(SECTION, 'enabled'):
        app.camera.clip_seconds = cfg.getfloat(SECTION, 'seconds')
        app.camera.clip_fps = cfg.getint(SECTION, 'fps')
        app.camera.clip_width = cfg.getint(SECTION, 'width')
    else:
        app.camera.clip_seconds = 0


def clip_seconds(cfg, capture_nbr):
    """Return the seconds of video kept before each capture of a sequence."""
    if capture_nbr == 1:
        return cfg.getfloat(SECTION, 'single_seconds')
    return cfg.getfloat(SECTION, 'seconds')


@pibooth.hookimpl
def state_preview_enter(cfg, app):
    """Longer clip for a 1-capture sequence."""
    if cv2 is not None and cfg.getboolean(SECTION, 'enabled'):
        app.camera.clip_seconds = clip_seconds(cfg, app.capture_nbr)


@pibooth.hookimpl
def state_wait_enter(app):
    app.previous_clip_file = None
    app.camera.drop_clip()


@pibooth.hookimpl(tryfirst=True)
def state_processing_exit(cfg, app):
    """Encode the clip next to the final picture (before the upload plugins)."""
    app.previous_clip_file = None
    frames = app.camera.get_clip()
    picture = getattr(app, 'previous_picture_file', None)
    if cv2 is None or not frames or not picture:
        return
    path = osp.splitext(picture)[0] + '.mp4'
    try:
        write_clip(path, frames, cfg.getint(SECTION, 'fps'), get_watermark())
        app.previous_clip_file = path
        LOGGER.info("Video clip saved: %s (%s frames)", path, len(frames))
    except Exception as ex:  # pylint: disable=broad-except
        LOGGER.error("Video clip not saved: %s", ex)


def get_watermark():
    """Return the (RGBA image, position, width ratio, opacity) watermark of the
    theme, or None.
    """
    options = theme.CURRENT.section('clip')
    path = theme.CURRENT.asset(options.get('watermark', 'logo'))
    if not path:
        return None
    image = Image.open(path).convert('RGBA')
    image = image.crop(image.getbbox())
    position = options.get('position', 'bottomright')
    if position not in POSITIONS:
        position = 'bottomright'
    return image, position, float(options.get('width', 0.22)), float(options.get('opacity', 0.9))


def watermark_layer(size, watermark):
    """Return the (BGR, alpha) arrays of the watermark placed on a frame of the
    given (width, height).
    """
    image, position, ratio, opacity = watermark
    width, height = size
    wm_width = max(1, int(width * ratio))
    mark = image.resize((wm_width, max(1, int(image.height * wm_width / image.width))), Image.LANCZOS)
    margin = int(width * 0.03)
    x = margin if 'left' in position else width - mark.width - margin
    y = margin if 'top' in position else height - mark.height - margin

    # Soft dark shadow under the mark: readable on bright and dark scenes
    shadow_alpha = Image.new('L', size, 0)
    shadow_alpha.paste(mark.getchannel('A'), (x, y + max(1, wm_width // 80)))
    shadow_alpha = shadow_alpha.filter(ImageFilter.GaussianBlur(max(2, wm_width // 30)))
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    layer.putalpha(shadow_alpha.point(lambda a: int(a * 0.6)))
    layer.alpha_composite(mark, (x, y))
    rgba = np.asarray(layer).astype(np.float32)
    bgr = rgba[:, :, 2::-1]
    alpha = (rgba[:, :, 3:] / 255.0) * opacity
    return bgr, alpha


def write_clip(path, frames, fps, watermark=None):
    """Write the BGR frames to an H.264 MP4 file (playable in the browsers and
    on the phones), with the optional watermark.
    """
    height, width = frames[0].shape[:2]
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'avc1'), fps, (width, height))
    if not writer.isOpened():
        raise IOError("No H.264 video encoder available")
    layer = watermark_layer((width, height), watermark) if watermark else None
    try:
        for frame in frames:
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))
            if layer is not None:
                bgr, alpha = layer
                frame = (frame * (1 - alpha) + bgr * alpha).astype(np.uint8)
            writer.write(frame)
    finally:
        writer.release()
