# -*- coding: utf-8 -*-

"""Pibooth themes: one folder holding the design tokens, fonts, assets, texts
and print templates of an event or a service.

A theme is a folder with a ``theme.json`` file::

    <theme>/
        theme.json      tokens (colors, fonts), texts, event info, templates
        fonts/          font files referenced by ``fonts``
        assets/         logos, mascots, booth background...
        templates/      print templates (pibooth JSON format)

It is selected with the ``[GENERAL][theme]`` option: a theme name looked up in
``<config dir>/themes/`` then in the themes shipped with pibooth, or the path
of a theme folder. When no theme is set, :py:data:`CURRENT` is an empty theme
and every caller falls back to its own default (the configuration values).

Values referenced in ``theme.json``:

- colors are ``#RRGGBB`` strings, or the name of another color (alias),
- ``booth``, ``qrcode`` and ``print`` sections map roles to color/font names,
- fonts are paths relative to the theme folder, or font names known by
  :py:func:`pibooth.fonts.get_filename` (shared fonts in ``pibooth/fonts``),
- ``booth.font_<lang>`` gives the booth font for a language (glyph coverage).
"""

import io
import os
import json
import os.path as osp

from pibooth.utils import LOGGER

THEMES_DIR = osp.join(osp.dirname(osp.abspath(__file__)), 'themes')
THEME_FILE = 'theme.json'


def to_rgb(value):
    """Return an (r, g, b) tuple from a ``#RRGGBB`` string or a sequence.
    """
    if isinstance(value, str):
        value = value.strip().lstrip('#')
        if len(value) == 3:
            value = ''.join(c * 2 for c in value)
        if len(value) != 6:
            raise ValueError("Invalid color '{}'".format(value))
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return tuple(int(c) for c in value[:3])
    raise ValueError("Invalid color '{}'".format(value))


class Theme(object):

    """Design tokens of a theme. An instance built without data is the empty
    theme: every lookup returns the given default.
    """

    def __init__(self, data=None, path=None):
        self.data = data or {}
        self.path = path

    def __bool__(self):
        return bool(self.data)

    @property
    def name(self):
        return self.data.get('name', osp.basename(self.path) if self.path else '')

    def section(self, name):
        """Return a section of the theme (empty dict if not defined).
        """
        return self.data.get(name) or {}

    def _resolve_color(self, name, depth=0):
        colors = self.section('colors')
        value = colors.get(name, name)
        if isinstance(value, str) and not value.startswith('#') and value in colors and depth < 8:
            return self._resolve_color(value, depth + 1)
        return value

    def color(self, name, default=None):
        """Return the RGB tuple of a color token (or ``#RRGGBB`` value), else
        the default.
        """
        if not name:
            return default
        value = self._resolve_color(name)
        try:
            return to_rgb(value)
        except ValueError:
            return default

    def role_color(self, section, role, default=None):
        """Return the color given to a role of a section (``booth``,
        ``qrcode``, ``print``...), e.g. ``role_color('booth', 'flash')``.
        """
        return self.color(self.section(section).get(role), default)

    def file(self, relpath):
        """Return the absolute path of a file of the theme, or None.
        """
        if not relpath or not self.path:
            return None
        path = relpath if osp.isabs(relpath) else osp.join(self.path, relpath)
        return path if osp.exists(path) else None

    def font(self, name, default=None):
        """Return the font (file path or font name) of a font token, e.g.
        ``font('display')``; a token may be an alias of another one.
        """
        fonts = self.section('fonts')
        value = fonts.get(name)
        if value in fonts:
            value = fonts[value]
        if not value:
            return default
        return self.file(value) or value

    def role_font(self, section, role, default=None):
        """Return the font given to a role of a section.
        """
        name = self.section(section).get(role)
        return self.font(name, default) if name else default

    def asset(self, name, default=None):
        """Return the absolute path of an asset declared in ``assets``.
        """
        return self.file(self.section('assets').get(name)) or default

    def role_asset(self, section, role, default=None):
        """Return the path of the asset given to a role of a section.
        """
        return self.asset(self.section(section).get(role), default)

    def text(self, key, lang, default=None, fallback=True):
        """Return a text of the theme in the given language. With
        ``fallback``, English then the first language defined are tried.
        """
        texts = self.section('texts')
        candidates = (lang, 'en') + tuple(texts) if fallback else (lang,)
        for candidate in candidates:
            if key in texts.get(candidate, {}):
                return texts[candidate][key]
        return default

    def event(self, key, default=None):
        return self.section('event').get(key, default)

    def templates(self):
        """Return the absolute paths of the print templates of the theme.
        """
        return [path for path in (self.file(rel) for rel in self.data.get('templates', [])) if path]


EMPTY = Theme()
CURRENT = EMPTY  # Dynamically set at startup


def find(name_or_path, config_dir=None):
    """Return the folder of the given theme, or None if not found.
    """
    if not name_or_path:
        return None
    candidates = [osp.abspath(osp.expanduser(name_or_path))]
    if config_dir:
        candidates.append(osp.join(osp.expanduser(config_dir), 'themes', name_or_path))
    candidates.append(osp.join(THEMES_DIR, name_or_path))
    for folder in candidates:
        if osp.isfile(osp.join(folder, THEME_FILE)):
            return folder
    return None


def load(name_or_path, config_dir=None):
    """Return the :py:class:`Theme` of the given name or folder, or the empty
    theme if not found or invalid.
    """
    if not name_or_path:
        return EMPTY
    folder = find(name_or_path, config_dir)
    if not folder:
        LOGGER.warning("Theme '%s' not found, fallback to the configuration values", name_or_path)
        return EMPTY
    try:
        with io.open(osp.join(folder, THEME_FILE), encoding='utf-8') as fp:
            data = json.load(fp)
    except (OSError, ValueError) as ex:
        LOGGER.error("Invalid theme '%s': %s", folder, ex)
        return EMPTY
    LOGGER.info("Theme '%s' loaded from '%s'", data.get('name', name_or_path), folder)
    return Theme(data, folder)


def get_available():
    """Return the names of the themes shipped with pibooth.
    """
    if not osp.isdir(THEMES_DIR):
        return []
    return sorted(name for name in os.listdir(THEMES_DIR) if osp.isfile(osp.join(THEMES_DIR, name, THEME_FILE)))
