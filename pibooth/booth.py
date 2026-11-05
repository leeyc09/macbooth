#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Pibooth main module.
"""

import os
import os.path as osp
import tempfile
import shutil
import logging
import argparse
import multiprocessing

import pygame

import pibooth
from pibooth import fonts
from pibooth import language, theme, pictures
from pibooth.counters import Counters
from pibooth.utils import (LOGGER, configure_logging, get_crash_message,
                           set_logging_level, get_event_pos)
from pibooth.states import StateMachine
from pibooth.plugins import create_plugin_manager
from pibooth.view import PiWindow
from pibooth.config import PiConfigParser, PiConfigMenu
from pibooth.printer import PRINTER_TASKS_UPDATED, Printer


class PiApplication(object):

    """Main class representing the ``pibooth`` software.
    The following attributes are available for use in plugins:

    :attr capture_nbr: number of capture to be done in the current sequence
    :type capture_nbr: int
    :attr capture_date: date (%Y-%m-%d-%H-%M-%S) of the first capture of the current sequence
    :type capture_date: str
    :attr capture_choices: possible choices of captures numbers.
    :type capture_choices: tuple
    :attr layout_choices: names of the layouts (picture templates) the user can choose among
    :type layout_choices: tuple
    :attr layout_nbr: index of the layout chosen in ``layout_choices``
    :type layout_nbr: int
    :attr layout_previews: preview of the final picture for each layout (during the 'layout' state)
    :type layout_previews: list
    :attr previous_picture: picture generated during last sequence
    :type previous_picture: :py:class:`PIL.Image`
    :attr previous_animated: infinite list of picture to display during animation
    :type previous_animated: :py:func:`itertools.cycle`
    :attr previous_picture_file: file name of the picture generated during last sequence
    :type previous_picture_file: str
    :attr count: holder for counter values
    :type count: :py:class:`pibooth.counters.Counters`
    :attr camera: camera used
    :type camera: :py:class:`pibooth.camera.base.BaseCamera`
    :attr printer: printer used
    :type printer: :py:class:`pibooth.printer.Printer`
    """

    def __init__(self, config, plugin_manager):
        self._pm = plugin_manager
        self._config = config

        # Create directories where pictures are saved
        for savedir in config.gettuple('GENERAL', 'directory', 'path'):
            if osp.isdir(savedir) and config.getboolean('GENERAL', 'debug'):
                shutil.rmtree(savedir)
            if not osp.isdir(savedir):
                os.makedirs(savedir)

        # Create window of (width, height)
        init_size = self._config.gettyped('WINDOW', 'size')
        init_debug = self._config.getboolean('GENERAL', 'debug')
        init_color, init_text_color = self._load_theme()

        title = 'Macbooth v{}'.format(pibooth.__version__)
        icon = theme.CURRENT.asset('app_icon') or pictures.get_filename('icon.png')
        if not isinstance(init_size, str):
            self._window = PiWindow(title, init_size, color=init_color,
                                    text_color=init_text_color, debug=init_debug, icon=icon)
        else:
            self._window = PiWindow(title, color=init_color,
                                    text_color=init_text_color, debug=init_debug, icon=icon)

        self._menu = None
        self._fingerdown_events = []

        # Define states of the application
        self._machine = StateMachine(self._pm, self._config, self, self._window)
        self._machine.add_state('wait')
        self._machine.add_state('choose')
        self._machine.add_state('chosen')
        self._machine.add_state('preview')
        self._machine.add_state('capture')
        self._machine.add_state('layout')
        self._machine.add_state('processing')
        self._machine.add_state('print')
        self._machine.add_state('finish')

        # ---------------------------------------------------------------------
        # Variables shared with plugins
        # Change them may break plugins compatibility
        self.capture_nbr = None
        self.capture_date = None
        self.capture_choices = (4, 1)
        self.layout_choices = ()
        self.layout_nbr = 0
        self.layout_previews = None
        self.previous_picture = None
        self.previous_animated = None
        self.previous_picture_file = None
        self.settings_changed = False  # Set by plugins changing the options while running

        self.count = Counters(self._config.join_path("counters.json"),
                              taken=0, printed=0, forgotten=0,
                              remaining_duplicates=self._config.getint('PRINTER', 'max_duplicates'))

        self.camera = self._pm.hook.pibooth_setup_camera(cfg=self._config, win=self._window)

        self.printer = Printer(config.get('PRINTER', 'printer_name'),
                               config.getint('PRINTER', 'max_pages'),
                               config.gettyped('PRINTER', 'printer_options'),
                               self.count)
        # ---------------------------------------------------------------------

    def _load_theme(self):
        """Load the theme of the configuration and return the window
        (background color or image, text color) it defines, the configuration
        values being used for the ones it does not define.
        """
        name = self._config.get('GENERAL', 'theme')
        if name != getattr(self, '_theme_name', None):  # Load once, or when changed in the settings
            theme.CURRENT = theme.load(name, osp.dirname(self._config.filename))
            self._theme_name = name
        color = self._config.gettyped('WINDOW', 'background')
        if not isinstance(color, (tuple, list)):
            color = self._config.getpath('WINDOW', 'background')
        text_color = self._config.gettyped('WINDOW', 'text_color')

        image = theme.CURRENT.role_asset('booth', 'background_image')
        color = image or theme.CURRENT.role_color('booth', 'background', color)
        text_color = theme.CURRENT.role_color('booth', 'text', text_color)
        # A theme may give a font per language (e.g. 'font_ko' for Hangul glyphs)
        fonts.CURRENT = fonts.get_filename(theme.CURRENT.role_font('booth', 'font_' + language.CURRENT)
                                           or theme.CURRENT.role_font('booth', 'font')
                                           or self._config.get('WINDOW', 'font'))
        return color, text_color

    def _initialize(self):
        """Restore the application with initial parameters defined in the
        configuration file.
        Only parameters that can be changed at runtime are restored.
        """
        # Handle the language configuration
        language.CURRENT = self._config.get('GENERAL', 'language')
        bg_color, text_color = self._load_theme()

        # Set the captures choices
        choices = self._config.gettuple('PICTURE', 'captures', int)
        for chx in choices:
            if chx not in [1, 2, 3, 4]:
                LOGGER.warning("Invalid captures number '%s' in config, fallback to '%s'",
                               chx, self.capture_choices)
                choices = self.capture_choices
                break
        self.capture_choices = choices

        self._window.arrow_location = self._config.get('WINDOW', 'arrows')
        self._window.arrow_offset = self._config.getint('WINDOW', 'arrows_x_offset')
        self._window.bg_color = bg_color
        self._window.text_color = text_color
        self._window.drop_cache()

        # Handle window size
        size = self._config.gettyped('WINDOW', 'size')
        if isinstance(size, str) and size.lower() == 'fullscreen':
            if not self._window.is_fullscreen:
                self._window.toggle_fullscreen()
        else:
            if self._window.is_fullscreen:
                self._window.toggle_fullscreen()
        self._window.debug = self._config.getboolean('GENERAL', 'debug')

        # Handle debug mode
        if not self._config.getboolean('GENERAL', 'debug'):
            set_logging_level()  # Restore default level
            self._machine.add_failsafe_state('failsafe')
        else:
            set_logging_level(logging.DEBUG)
            self._machine.remove_state('failsafe')

        # Reset the print counter (in case of max_pages is reached)
        self.printer.max_pages = self._config.getint('PRINTER', 'max_pages')

    def update_layouts(self):
        """Refresh the list of the layouts (picture templates) available for
        the number of captures of the current sequence. Reset the chosen layout
        to the first one.

        :return: the available layout names
        :rtype: tuple
        """
        self.layout_choices = tuple(self._pm.hook.pibooth_setup_layouts(
            cfg=self._config, capture_nbr=self.capture_nbr) or ())
        self.layout_nbr = 0
        return self.layout_choices

    @property
    def picture_filename(self):
        """Return the final picture file name.
        """
        if not self.capture_date:
            raise EnvironmentError("The 'capture_date' attribute is not set yet")
        return "{}_pibooth.jpg".format(self.capture_date)

    def find_quit_event(self, events):
        """Return the first found event if found in the list.
        """
        for event in events:
            if event.type == pygame.QUIT:
                return event
        return None

    def find_settings_event(self, events):
        """Return the first found event if found in the list.
        """
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return event
            if event.type == pygame.FINGERDOWN:
                # Press but not release
                self._fingerdown_events.append(event)
            if event.type == pygame.FINGERUP:
                # Resetting touch_events
                self._fingerdown_events = []
            if len(self._fingerdown_events) > 3:
                # 4 fingers on the screen trigger the menu
                self._fingerdown_events = []
                return event
        return None

    def find_fullscreen_event(self, events):
        """Return the first found event if found in the list.
        """
        for event in events:
            if event.type == pygame.KEYDOWN and \
                    event.key == pygame.K_f and pygame.key.get_mods() & pygame.KMOD_CTRL:
                return event
        return None

    def find_resize_event(self, events):
        """Return the first found event if found in the list.
        """
        for event in events:
            if event.type == pygame.VIDEORESIZE:
                return event
        return None

    def find_capture_event(self, events):
        """Return the first found event if found in the list.
        """
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                return event
            if (event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3)) or event.type == pygame.FINGERUP:
                pos = get_event_pos(self._window.display_size, event)
                rect = self._window.get_rect()
                if pygame.Rect(0, 0, rect.width // 2, rect.height).collidepoint(pos):
                    return event
        return None

    def find_print_event(self, events):
        """Return the first found event if found in the list.
        """
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_e\
                    and pygame.key.get_mods() & pygame.KMOD_CTRL:
                return event
            if (event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3)) or event.type == pygame.FINGERUP:
                pos = get_event_pos(self._window.display_size, event)
                rect = self._window.get_rect()
                if pygame.Rect(rect.width // 2, 0, rect.width // 2, rect.height).collidepoint(pos):
                    return event
        return None

    def find_print_status_event(self, events):
        """Return the first found event if found in the list.
        """
        for event in events:
            if event.type == PRINTER_TASKS_UPDATED:
                return event
        return None

    def find_layout_event(self, events):
        """Return the first found event related to the layout choice. The
        ``event.layout`` attribute is set to 'previous', 'next', 'validate'
        or to the index of the layout selected on the screen.
        """
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
                event.layout = 'previous'
                return event
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                event.layout = 'next'
                return event
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_RETURN, pygame.K_KP_ENTER):
                event.layout = 'validate'
                return event
            if (event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3)) or event.type == pygame.FINGERUP:
                pos = get_event_pos(self._window.display_size, event)
                index = self._window.get_layout_index(pos)
                if index is None:
                    continue
                event.layout = 'validate' if index < 0 else index
                return event
        return None

    def find_choice_event(self, events):
        """Return the first found event if found in the list.
        """
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
                return event
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                return event
            if (event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3)) or event.type == pygame.FINGERUP:
                pos = get_event_pos(self._window.display_size, event)
                rect = self._window.get_rect()
                if pygame.Rect(0, 0, rect.width // 2, rect.height).collidepoint(pos):
                    event.key = pygame.K_LEFT
                else:
                    event.key = pygame.K_RIGHT
                return event
        return None

    def main_loop(self):
        try:
            fps = 40
            clock = pygame.time.Clock()
            self._initialize()
            self._pm.hook.pibooth_startup(cfg=self._config, app=self)
            self._machine.set_state('wait')

            while True:
                events = list(pygame.event.get())

                if self.find_quit_event(events):
                    break

                if self.find_fullscreen_event(events):
                    self._window.toggle_fullscreen()

                event = self.find_resize_event(events)
                if event:
                    self._window.resize(event.size)

                if not self._menu and self.find_settings_event(events):
                    self.camera.stop_preview()
                    self._menu = PiConfigMenu(self._pm, self._config, self, self._window)
                    self._menu.show()
                elif self._menu and self._menu.is_shown():
                    self._menu.process(events)
                elif self._menu and not self._menu.is_shown():
                    self._initialize()
                    self._machine.set_state('wait')
                    self._menu = None
                elif self.settings_changed and self._machine.active_state == 'wait':
                    # Options saved by a plugin (e.g. a settings web page): apply
                    # them like after the menu, only between two sessions
                    self.settings_changed = False
                    LOGGER.info("Applying the changed settings")
                    self._initialize()
                    self._machine.set_state('wait')
                else:
                    self._machine.process(events)

                pygame.display.update()
                clock.tick(fps)  # Ensure the program will never run at more than <fps> frames per second

        except Exception as ex:
            LOGGER.error(str(ex), exc_info=True)
            LOGGER.error(get_crash_message())
        finally:
            self._pm.hook.pibooth_cleanup(app=self)
            pygame.quit()


def main():
    """Application entry point.
    """
    if hasattr(multiprocessing, 'set_start_method'):
        # Avoid use 'fork': safely forking a multithreaded process is problematic
        multiprocessing.set_start_method('spawn')

    parser = argparse.ArgumentParser(usage="%(prog)s [options]", description=pibooth.__doc__)

    parser.add_argument("config_directory", nargs='?', default="~/.config/pibooth",
                        help=u"path to configuration directory (default: %(default)s)")

    parser.add_argument('--version', action='version', version=pibooth.__version__,
                        help=u"show program's version number and exit")

    parser.add_argument("--config", action='store_true',
                        help=u"edit the current configuration and exit")

    parser.add_argument("--translate", action='store_true',
                        help=u"edit the GUI translations and exit")

    parser.add_argument("--reset", action='store_true',
                        help=u"restore the default configuration/translations and exit")

    parser.add_argument("--nolog", action='store_true', default=False,
                        help=u"don't save console output in a file (avoid filling the /tmp directory)")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", dest='logging', action='store_const', const=logging.DEBUG,
                       help=u"report more information about operations", default=logging.INFO)
    group.add_argument("-q", "--quiet", dest='logging', action='store_const', const=logging.WARNING,
                       help=u"report only errors and warnings", default=logging.INFO)

    options = parser.parse_args()

    if not options.nolog:
        filename = osp.join(tempfile.gettempdir(), 'pibooth.log')
    else:
        filename = None
    configure_logging(options.logging, '[ %(levelname)-8s] %(name)-18s: %(message)s', filename=filename)

    plugin_manager = create_plugin_manager()

    # Load the configuration
    config = PiConfigParser(osp.join(options.config_directory, "pibooth.cfg"), plugin_manager, not options.reset)

    # Register plugins
    plugin_manager.load_all_plugins(config.gettuple('GENERAL', 'plugins', 'path'),
                                    config.gettuple('GENERAL', 'plugins_disabled', str))
    LOGGER.info("Installed plugins: %s", ", ".join(
        [plugin_manager.get_friendly_name(p) for p in plugin_manager.list_external_plugins()]))

    # Load the languages
    language.init(config.join_path("translations.cfg"), options.reset)

    # Update configuration with plugins ones
    plugin_manager.hook.pibooth_configure(cfg=config)

    # Ensure config files are present in case of first pibooth launch
    if not options.reset:
        if not osp.isfile(config.filename):
            config.save(default=True)
        plugin_manager.hook.pibooth_reset(cfg=config, hard=False)

    if options.config:
        LOGGER.info("Editing the pibooth configuration...")
        config.edit()
    elif options.translate:
        LOGGER.info("Editing the GUI translations...")
        language.edit()
    elif options.reset:
        config.save(default=True)
        plugin_manager.hook.pibooth_reset(cfg=config, hard=True)
    else:
        LOGGER.info("Starting the photo booth application")
        app = PiApplication(config, plugin_manager)
        app.main_loop()


if __name__ == '__main__':
    main()
