# -*- coding: utf-8 -*-

"""Tests of the QR code plugin placement (scaled with the window)."""

import sys
import os.path as osp
import pygame
import pytest

sys.path.insert(0, osp.join(osp.dirname(osp.dirname(osp.abspath(__file__))), 'plugins'))
import pibooth_qrcode as qrp  # noqa: E402


class Cfg(object):
    def __init__(self, **values):
        self.values = dict({'size': 240, 'offset': (40, 40), 'wait_location': 'topleft',
                            'side_text': '', 'foreground': (0, 0, 0), 'background': (255, 255, 255)}, **values)

    def get(self, section, option):
        return self.values[option]

    def getint(self, section, option):
        return int(self.values[option])

    def gettuple(self, section, option, types, extend=0):
        return tuple(self.values[option])

    def gettyped(self, section, option):
        return self.values.get(option, (255, 255, 255))


class App(object):
    def __init__(self):
        self.previous_qr_base = pygame.Surface((37, 37))
        self.previous_qr = None
        self.previous_picture = object()


class Win(object):
    def __init__(self, size):
        self.surface = pygame.Surface(size)

    def get_rect(self):
        return self.surface.get_rect()


@pytest.mark.parametrize('size, expected_qr, expected_offset', [
    ((1280, 720), 240, 40),
    ((1920, 1080), 360, 60),
    ((800, 480), 160, 26),
])
def test_qrcode_is_scaled_with_the_window(size, expected_qr, expected_offset):
    cfg, app, win = Cfg(), App(), Win(size)
    qrp.state_wait_enter(cfg, app, win)
    assert app.previous_qr.get_size() == (expected_qr, expected_qr)
    assert app.qr_rect.topleft == (expected_offset, expected_offset)


def test_scaled_qrcode_is_cached_until_the_window_changes():
    cfg, app = Cfg(), App()
    first = qrp.get_scaled_qr(cfg, app, pygame.Rect(0, 0, 1280, 720))
    assert qrp.get_scaled_qr(cfg, app, pygame.Rect(0, 0, 1280, 720)) is first
    assert qrp.get_scaled_qr(cfg, app, pygame.Rect(0, 0, 1920, 1080)).get_width() == 360


def test_size_zero_keeps_the_generated_size():
    cfg, app = Cfg(size=0), App()
    assert qrp.get_scaled_qr(cfg, app, pygame.Rect(0, 0, 1920, 1080)).get_width() == 37


def test_qrcode_follows_a_window_resize_on_the_wait_view():
    cfg, app, win = Cfg(), App(), Win((1280, 720))
    qrp.state_wait_enter(cfg, app, win)
    assert app.previous_qr.get_width() == 240
    win.surface = pygame.Surface((3600, 2025))   # Switched to a big full screen
    qrp.state_wait_do(cfg, app, win)
    assert app.previous_qr.get_width() == 675     # Same proportion: 240 / 720 * 2025
    assert app.qr_rect.topleft == (112, 112)
