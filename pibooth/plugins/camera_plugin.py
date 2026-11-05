# -*- coding: utf-8 -*-

import time
import pygame
import pibooth
from pibooth import camera, sounds
from pibooth.camera.chooser import PiCameraChooser, AUTO
from pibooth.utils import LOGGER

ASK = 'ask'  # Value of the 'opencv_camera' option to display the chooser at startup


class CameraPlugin(object):

    """Plugin to manage the camera captures.
    """

    name = 'pibooth-core:camera'

    def __init__(self, plugin_manager):
        self._pm = plugin_manager
        self.count = 0

    @pibooth.hookimpl(hookwrapper=True)
    def pibooth_setup_camera(self, cfg, win):
        outcome = yield  # all corresponding hookimpls are invoked here
        cam = outcome.get_result()
        sounds.preload()

        if not cam:
            LOGGER.debug("Fallback to pibooth default camera management system")
            webcam = self._get_opencv_camera(cfg)
            if webcam == ASK:
                webcam = PiCameraChooser(win).run()
                if webcam == AUTO:
                    webcam = None
            cam = camera.find_camera(webcam)

        cam.initialize(cfg.gettuple('CAMERA', 'iso', (int, str), 2),
                       cfg.gettyped('CAMERA', 'resolution'),
                       cfg.gettuple('CAMERA', 'rotation', int, 2),
                       cfg.getboolean('CAMERA', 'flip'),
                       cfg.getboolean('CAMERA', 'delete_internal_memory'),
                       cfg.get('CAMERA', 'autofocus'),
                       cfg.getfloat('CAMERA', 'lens_position'))
        outcome.force_result(cam)

    @staticmethod
    def _get_opencv_camera(cfg):
        """Return the webcam wanted by the configuration: a port number, a part
        of the webcam name, :py:data:`ASK` to display a chooser at startup, or
        None for the first webcam found.
        """
        value = cfg.get('CAMERA', 'opencv_camera').strip().strip('"\'')
        if value.lower() == ASK:
            return ASK
        try:
            port = int(value)
        except ValueError:
            return value or None
        return port if port >= 0 else None

    @pibooth.hookimpl
    def pibooth_cleanup(self, app):
        app.camera.quit()

    @pibooth.hookimpl
    def state_failsafe_enter(self, app):
        """Reset variables set in this plugin.
        """
        app.capture_date = None
        app.capture_nbr = None
        app.camera.drop_captures()  # Flush previous captures
        app.camera.drop_clip()

    @pibooth.hookimpl
    def state_wait_enter(self, app):
        app.capture_date = None
        if len(app.capture_choices) > 1:
            app.capture_nbr = None
        else:
            app.capture_nbr = app.capture_choices[0]

    @pibooth.hookimpl
    def state_choose_do(self, app, events):
        event = app.find_choice_event(events)
        if event:
            if event.key == pygame.K_LEFT:
                app.capture_nbr = app.capture_choices[0]
            elif event.key == pygame.K_RIGHT:
                app.capture_nbr = app.capture_choices[1]

    @pibooth.hookimpl
    def state_preview_enter(self, cfg, app, win):
        LOGGER.info("Show preview before next capture")
        if not app.capture_date:
            app.capture_date = time.strftime("%Y-%m-%d-%H-%M-%S")
        app.camera.preview(win)

    @pibooth.hookimpl
    def state_preview_do(self, cfg, app):
        pygame.event.pump()  # Before blocking actions
        if cfg.getboolean('WINDOW', 'preview_countdown'):
            app.camera.preview_countdown(cfg.getint('WINDOW', 'preview_delay'))
        else:
            app.camera.preview_wait(cfg.getint('WINDOW', 'preview_delay'))

    @pibooth.hookimpl
    def state_preview_exit(self, cfg, app):
        if cfg.getboolean('WINDOW', 'preview_stop_on_capture'):
            app.camera.stop_preview()

    @pibooth.hookimpl
    def state_capture_do(self, cfg, app, win):
        effects = cfg.gettyped('PICTURE', 'captures_effects')
        if not isinstance(effects, (list, tuple)):
            # Same effect for all captures
            effect = effects
        elif len(effects) >= app.capture_nbr:
            # Take the effect corresponding to the current capture
            effect = effects[self.count]
        else:
            # Not possible
            raise ValueError("Not enough effects defined for {} captures {}".format(
                app.capture_nbr, effects))

        LOGGER.info("Take a capture")
        sounds.shutter()
        if cfg.getboolean('WINDOW', 'flash'):
            with win.flash(2):  # Manage the window here, have no choice
                app.camera.capture(effect)
        else:
            app.camera.capture(effect)

        self.count += 1

    @pibooth.hookimpl
    def state_capture_exit(self, cfg, app):
        if not cfg.getboolean('WINDOW', 'preview_stop_on_capture'):
            app.camera.stop_preview()

    @pibooth.hookimpl
    def state_processing_enter(self, app):
        self.count = 0
