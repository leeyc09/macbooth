# -*- coding: utf-8 -*-

"""Menu displayed at startup to choose the webcam among the ones seen by OpenCV.
"""

import sys
import pygame
import pygame_menu as pgm
from pibooth import fonts
from pibooth.utils import LOGGER
from pibooth.config.menu import THEME_DARK
from pibooth.camera.opencv import get_cv_camera_names, get_cv_camera_proxy

# System fonts able to draw the webcam names in any language (the fonts
# shipped with pibooth only have latin glyphs), the first one found is used
CJK_FONTS = ('applesdgothicneo', 'notosanscjkkr', 'notosanscjk', 'nanumgothic',
             'malgungothic', 'notosanscjkjp', 'arialunicode')

AUTO = -1  # Let pibooth use the first webcam found


def _menu_font():
    """Return the file name of a font able to draw the webcam names.
    """
    for name in CJK_FONTS:
        filename = pygame.font.match_font(name)
        if filename:
            return filename
    return fonts.get_filename("Monoid-Retina")


def list_webcams():
    """Return the list of (port, label) of the webcams seen by OpenCV. When the
    names are not available on the platform, the 3 first ports are probed.
    """
    names = get_cv_camera_names()
    if names:
        return [(port, "{}: {}".format(port, name or "Webcam")) for port, name in enumerate(names)]
    webcams = []
    for port in range(3):
        proxy = get_cv_camera_proxy(port)
        if proxy:
            proxy.release()
            webcams.append((port, "{}: Webcam".format(port)))
    return webcams


class PiCameraChooser(object):

    """Blocking menu to choose the webcam. :py:meth:`run` returns the chosen
    OpenCV port, or :py:data:`AUTO` to let pibooth choose.
    """

    def __init__(self, window, list_func=list_webcams):
        self.win = window
        self._list_func = list_func
        self._chosen = None
        self._menu = None
        self._build()

    def _build(self):
        """Build (or rebuild) the menu with the webcams currently seen.
        """
        theme = THEME_DARK.copy()
        theme.widget_font = _menu_font()
        theme.title_font_size = 28
        theme.widget_font_size = 22
        theme.widget_margin = (0, 12)
        size = self.win.get_rect().size
        self._menu = pgm.Menu(title="Choose the camera",
                              width=min(700, size[0]),
                              height=min(480, size[1]),
                              theme=theme,
                              touchscreen=True,
                              onclose=pgm.events.NONE)
        webcams = self._list_func()
        LOGGER.debug("Webcams proposed: %s", webcams)
        if webcams:
            for port, label in webcams:
                self._menu.add.button(label, self._on_choose, port)
        else:
            self._menu.add.label("No webcam found")
        self._menu.add.vertical_margin(10)
        self._menu.add.button("Refresh the list", self._on_refresh)
        self._menu.add.button("Auto (first webcam found)", self._on_choose, AUTO)
        self._menu.add.button("Quit", self._on_quit)

    def _on_choose(self, port):
        self._chosen = port

    def _on_refresh(self):
        self._build()

    @staticmethod
    def _on_quit():
        LOGGER.info("Quit from the camera chooser")
        sys.exit(0)

    def process(self, events):
        """Process the events and draw the menu. Return the chosen port or
        None while nothing is chosen.
        """
        for event in events:
            if event.type == pygame.QUIT:
                self._on_quit()
            if event.type == pygame.VIDEORESIZE:
                self.win.resize(event.size)
                self._build()
        self._menu.update(events)
        if self._chosen is None:
            self.win.surface.fill(THEME_DARK.background_color)
            self._menu.draw(self.win.surface)
            pygame.display.update()
        return self._chosen

    def run(self, fps=30):
        """Display the menu until a webcam is chosen. Return the chosen port
        (or :py:data:`AUTO`).
        """
        clock = pygame.time.Clock()
        while self.process(pygame.event.get()) is None:
            clock.tick(fps)
        if self._chosen == AUTO:
            LOGGER.info("Camera chooser: first webcam found will be used")
        else:
            LOGGER.info("Camera chooser: webcam on port %s selected", self._chosen)
        return self._chosen
