# -*- coding: utf-8 -*-

import pytest
import pygame
import pygame_menu as pgm
from pibooth.camera.chooser import PiCameraChooser, AUTO
from pibooth.view.window import PiWindow


def key(code):
    return pygame.event.Event(pygame.KEYDOWN, key=code, unicode='', mod=0, scancode=0, window=None, test=True)


@pytest.fixture
def window():
    return PiWindow("Test", (800, 480))


@pytest.fixture
def webcams():
    return {'list': [(0, u"0: MacBook Pro 카메라"), (1, "1: OBS Virtual Camera")], 'calls': 0}


@pytest.fixture
def chooser(window, webcams):
    def list_func():
        webcams['calls'] += 1
        return webcams['list']
    return PiCameraChooser(window, list_func)


def test_first_webcam_is_selected_by_default(chooser):
    assert chooser.process([]) is None
    assert chooser.process([key(pgm.controls.KEY_APPLY)]) == 0


def test_second_webcam_can_be_chosen(chooser):
    chooser.process([key(pgm.controls.KEY_MOVE_UP)])  # Next widget
    assert chooser.process([key(pgm.controls.KEY_APPLY)]) == 1


def test_auto_choice(chooser, webcams):
    for _ in range(len(webcams['list']) + 1):  # Skip the webcams and 'Refresh'
        chooser.process([key(pgm.controls.KEY_MOVE_UP)])
    assert chooser.process([key(pgm.controls.KEY_APPLY)]) == AUTO


def test_refresh_lists_the_webcams_again(chooser, webcams):
    assert webcams['calls'] == 1
    webcams['list'] = [(2, "2: iPhone")]
    for _ in range(len(webcams['list']) + 1):  # Go to 'Refresh'
        chooser.process([key(pgm.controls.KEY_MOVE_UP)])
    assert chooser.process([key(pgm.controls.KEY_APPLY)]) is None
    assert webcams['calls'] == 2
    # The first button is now the new webcam
    assert chooser.process([key(pgm.controls.KEY_APPLY)]) == 2


def test_no_webcam_still_offers_refresh_and_auto(window):
    chooser = PiCameraChooser(window, lambda: [])
    chooser.process([key(pgm.controls.KEY_MOVE_UP)])  # 'Refresh' -> 'Auto'
    assert chooser.process([key(pgm.controls.KEY_APPLY)]) == AUTO


def test_quit_event_exits(chooser):
    with pytest.raises(SystemExit):
        chooser.process([pygame.event.Event(pygame.QUIT)])


def test_run_returns_the_choice(chooser):
    pygame.event.post(key(pgm.controls.KEY_APPLY))
    assert chooser.run() == 0
