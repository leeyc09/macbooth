# -*- coding: utf-8 -*-

"""Render the look of a theme to PNG/JPEG files, to check a design change
without starting the booth.

Usage::

    python tools/preview_theme.py <theme name or folder> [--out preview] [--screens]

It writes into the output folder:

- ``<template>.jpg``: each print template of the theme, filled with the
  sample captures of ``tests/captures`` (the real final picture engine),
- with ``--screens``: ``screen-wait.png``, ``screen-choose.png``,
  ``screen-layout.png`` and ``screen-processing.png``, the booth screens
  drawn with the theme (1600x900, Korean texts).
"""

import os
import sys
import argparse
import tempfile
import os.path as osp

ROOT = osp.dirname(osp.dirname(osp.abspath(__file__)))
sys.path[:0] = [ROOT, osp.join(ROOT, 'plugins')]
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from PIL import Image  # noqa: E402
from pibooth import theme as themes  # noqa: E402

CAPTURES = [osp.join(ROOT, 'tests', 'captures', 'portrait', name)
            for name in ('capture0.png', 'capture1.png', 'capture2.png', 'capture3.jpg')]


def render_templates(theme, out):
    """Render each print template of the theme, return the written paths."""
    import pibooth_picture_template as ppt  # pylint: disable=import-outside-toplevel
    captures = [Image.open(path).convert('RGB') for path in CAPTURES]
    written = []
    for path in theme.templates():
        if not path.lower().endswith('.json'):
            print("Skipped (not a JSON template):", path)
            continue
        template = ppt.JsonTemplate(path)
        factory = template.build_factory(template.orientation, captures[:template.captures])
        target = osp.join(out, osp.splitext(osp.basename(path))[0] + '.jpg')
        factory.build().convert('RGB').save(target, quality=90)
        written.append(target)
    return written


def render_screens(theme, pictures, out, language='ko'):
    """Draw the main booth screens with the theme, return the written paths."""
    # pylint: disable=import-outside-toplevel
    import pygame
    from pibooth import fonts, language as languages
    from pibooth.view import PiWindow
    languages.init(osp.join(tempfile.mkdtemp(), 'translations.cfg'))  # Default texts
    languages.CURRENT = language
    themes.CURRENT = theme
    image = theme.role_asset('booth', 'background_image')
    color = image or theme.role_color('booth', 'background', (0, 0, 0))
    text_color = theme.role_color('booth', 'text', (255, 255, 255))
    fonts.CURRENT = fonts.get_filename(theme.role_font('booth', 'font_' + language)
                                       or theme.role_font('booth', 'font') or 'Amatic-Bold')
    win = PiWindow('preview', (1600, 900), color=color, text_color=text_color, arrow_location='hidden')
    picture = pictures[0] if pictures else None
    screens = (('wait', lambda: win.show_intro(picture, False)),
               ('choose', lambda: win.show_choice((4, 1))),
               ('layout', lambda: win.show_layout(pictures, 0)),
               ('processing', win.show_work_in_progress))
    written = []
    for name, show in screens:
        if name == 'layout' and not pictures:
            continue
        win._current_foreground = None  # pylint: disable=protected-access
        show()
        win.update()
        target = osp.join(out, 'screen-{}.png'.format(name))
        pygame.image.save(win.surface, target)
        written.append(target)
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument("theme", help="theme name or folder")
    parser.add_argument("--out", default="preview", help="output folder (default: preview)")
    parser.add_argument("--screens", action='store_true', help="also draw the booth screens")
    options = parser.parse_args()

    theme = themes.load(options.theme)
    if theme is themes.EMPTY:
        parser.error("theme '{}' not found".format(options.theme))
    os.makedirs(options.out, exist_ok=True)
    written = render_templates(theme, options.out)
    if options.screens:
        written += render_screens(theme, [Image.open(path) for path in written], options.out)
    for path in written:
        print("Wrote", path)


if __name__ == '__main__':
    main()
