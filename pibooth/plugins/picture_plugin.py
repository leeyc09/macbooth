# -*- coding: utf-8 -*-

import os
import os.path as osp
import itertools
from datetime import datetime
import pibooth
from pibooth.utils import LOGGER, PoolingTimer
from pibooth.pictures import get_picture_factory
from pibooth.pictures.pool import PicturesFactoryPool


class PicturePlugin(object):

    """Plugin to build the final picture.
    """

    name = 'pibooth-core:picture'

    def __init__(self, plugin_manager):
        self._pm = plugin_manager
        self.factory_pool = PicturesFactoryPool()
        self.picture_destroy_timer = PoolingTimer(0)
        self.second_previous_picture = None
        self.texts_vars = {}
        self._captures = None  # Captures kept between the 'layout' and 'processing' states
        self._layout_factories = []  # Factory of each layout built for the previews
        self._layout_do_calls = 0

    def _reset_vars(self, app):
        """Destroy final picture (can not be used anymore).
        """
        self.factory_pool.clear()
        app.previous_picture = None
        app.previous_animated = None
        app.previous_picture_file = None

    @pibooth.hookimpl(hookwrapper=True)
    def pibooth_setup_picture_factory(self, cfg, opt_index, factory):

        outcome = yield  # all corresponding hookimpls are invoked here
        factory = outcome.get_result() or factory

        factory.set_margin(cfg.getint('PICTURE', 'margin_thick'))

        backgrounds = cfg.gettuple('PICTURE', 'backgrounds', ('color', 'path'), 2)
        factory.set_background(backgrounds[opt_index])

        overlays = cfg.gettuple('PICTURE', 'overlays', 'path', 2)
        if overlays[opt_index]:
            factory.set_overlay(overlays[opt_index])

        texts = [cfg.get('PICTURE', 'footer_text1').strip('"').format(**self.texts_vars),
                 cfg.get('PICTURE', 'footer_text2').strip('"').format(**self.texts_vars)]
        colors = cfg.gettuple('PICTURE', 'text_colors', 'color', len(texts))
        text_fonts = cfg.gettuple('PICTURE', 'text_fonts', str, len(texts))
        alignments = cfg.gettuple('PICTURE', 'text_alignments', str, len(texts))
        if any(elem != '' for elem in texts):
            for params in zip(texts, text_fonts, colors, alignments):
                factory.add_text(*params)

        if cfg.getboolean('PICTURE', 'captures_cropping'):
            factory.set_cropping()

        if cfg.getboolean('GENERAL', 'debug'):
            factory.set_outlines()

        outcome.force_result(factory)

    @pibooth.hookimpl
    def pibooth_cleanup(self):
        self.factory_pool.quit()

    @pibooth.hookimpl
    def state_failsafe_enter(self, app):
        self._reset_vars(app)
        self._captures = None
        self._layout_factories = []
        app.layout_previews = None

    @pibooth.hookimpl
    def state_wait_enter(self, cfg, app):
        animated = self.factory_pool.get()
        if cfg.getfloat('WINDOW', 'wait_picture_delay') == 0:
            # Do it here to avoid a transient display of the picture
            self._reset_vars(app)
        elif animated:
            app.previous_animated = itertools.cycle(animated)

        # Reset timeout in case of settings changed
        self.picture_destroy_timer.timeout = max(0, cfg.getfloat('WINDOW', 'wait_picture_delay'))
        self.picture_destroy_timer.start()

    @pibooth.hookimpl
    def state_wait_do(self, cfg, app):
        if cfg.getfloat('WINDOW', 'wait_picture_delay') > 0 and self.picture_destroy_timer.is_timeout()\
                and app.previous_picture_file:
            self._reset_vars(app)

    def _setup_factory(self, cfg, app, captures, layout_index, **kwargs):
        """Return the picture factory configured by the plugins for the given
        captures and layout.
        """
        default_factory = get_picture_factory(captures, cfg.get('PICTURE', 'orientation'), **kwargs)
        return self._pm.hook.pibooth_setup_picture_factory(cfg=cfg,
                                                           opt_index=app.capture_choices.index(app.capture_nbr),
                                                           factory=default_factory,
                                                           layout_index=layout_index)

    def _set_texts_vars(self, app):
        """Update the variables usable in the texts of the final picture.
        """
        self.texts_vars['date'] = datetime.strptime(app.capture_date, "%Y-%m-%d-%H-%M-%S")
        self.texts_vars['count'] = app.count

    @pibooth.hookimpl
    def state_layout_enter(self, app):
        app.layout_nbr = 0
        app.layout_previews = None
        self._layout_factories = []
        self._layout_do_calls = 0

    @pibooth.hookimpl
    def state_layout_do(self, cfg, app, events):
        self._layout_do_calls += 1
        if self._layout_do_calls == 1:
            return  # Let the window display the wait view before the (long) previews build

        if app.layout_previews is None:
            self._set_texts_vars(app)
            self._captures = app.camera.get_captures()
            LOGGER.info("Building the preview of the %s picture templates", len(app.layout_choices))
            previews = []
            for layout_index in range(len(app.layout_choices)):
                factory = self._setup_factory(cfg, app, self._captures, layout_index)
                preview = factory.build().copy()
                preview.thumbnail((1200, 1200))
                previews.append(preview)
                self._layout_factories.append(factory)
            app.layout_previews = previews

        event = app.find_layout_event(events)
        if event:
            if event.layout == 'previous':
                app.layout_nbr = (app.layout_nbr - 1) % len(app.layout_choices)
            elif event.layout == 'next':
                app.layout_nbr = (app.layout_nbr + 1) % len(app.layout_choices)
            elif isinstance(event.layout, int) and 0 <= event.layout < len(app.layout_choices):
                app.layout_nbr = event.layout

    @pibooth.hookimpl
    def state_layout_exit(self, app):
        app.layout_previews = None  # Free the memory, the factories are kept for 'processing'

    @pibooth.hookimpl
    def state_processing_enter(self, app):
        self.second_previous_picture = app.previous_picture
        self._reset_vars(app)

    @pibooth.hookimpl
    def state_processing_do(self, cfg, app):
        self._set_texts_vars(app)

        LOGGER.info("Saving raw captures")
        if self._captures is None:
            self._captures = app.camera.get_captures()
        captures = self._captures
        self._captures = None

        for savedir in cfg.gettuple('GENERAL', 'directory', 'path'):
            rawdir = osp.join(savedir, "raw", app.capture_date)
            os.makedirs(rawdir)

            for capture in captures:
                count = captures.index(capture)
                capture.save(osp.join(rawdir, "pibooth{:03}.jpg".format(count)))

        LOGGER.info("Creating the final picture")
        if 0 <= app.layout_nbr < len(self._layout_factories):
            factory = self._layout_factories[app.layout_nbr]  # Already built for the preview
        else:
            factory = self._setup_factory(cfg, app, captures, app.layout_nbr)
        self._layout_factories = []
        app.previous_picture = factory.build()

        for savedir in cfg.gettuple('GENERAL', 'directory', 'path'):
            app.previous_picture_file = osp.join(savedir, app.picture_filename)
            factory.save(app.previous_picture_file)

        if cfg.getboolean('WINDOW', 'animate') and app.capture_nbr > 1:
            LOGGER.info("Asyncronously generate pictures for animation")
            for capture in captures:
                factory = self._setup_factory(cfg, app, (capture,), app.layout_nbr, force_pil=True, dpi=200)
                factory.set_margin(factory._margin // 3)  # 1/3 since DPI is divided by 3
                self.factory_pool.add(factory)

    @pibooth.hookimpl
    def state_processing_exit(self, app):
        app.count.taken += 1  # Do it here because 'print' state can be skipped

    @pibooth.hookimpl
    def state_print_do(self, cfg, app, events):
        if app.find_capture_event(events):

            LOGGER.info("Moving the picture in the forget folder")
            for savedir in cfg.gettuple('GENERAL', 'directory', 'path'):
                forgetdir = osp.join(savedir, "forget")
                if not osp.isdir(forgetdir):
                    os.makedirs(forgetdir)
                os.rename(osp.join(savedir, app.picture_filename), osp.join(forgetdir, app.picture_filename))

            self._reset_vars(app)
            app.count.forgotten += 1
            app.previous_picture = self.second_previous_picture

            # Deactivate the print function for the backuped picture
            # as we don't known how many times it has already been printed
            app.count.remaining_duplicates = 0
