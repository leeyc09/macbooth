# -*- coding: utf-8 -*-

import os
import os.path as osp
import fnmatch
from difflib import SequenceMatcher
import pygame
from PIL import ImageFont, ImageDraw


EMBEDDED_FONT_PATH = osp.dirname(osp.abspath(__file__))


def _font_getsize(self, text, *args, **kwargs):
    """Size (width, height) of the text, as returned by Pillow < 10.
    """
    _left, _top, right, bottom = self.getbbox(text, *args, **kwargs)
    return right, bottom


def _draw_textsize(self, text, font=None, *args, **kwargs):
    """Size (width, height) of the text, as returned by Pillow < 10.
    """
    _left, _top, right, bottom = self.textbbox((0, 0), text, font, *args, **kwargs)
    return right, bottom


# Pillow 10 removed 'FreeTypeFont.getsize()' and 'ImageDraw.textsize()', but
# several plugins written before still call them (pibooth-picture-template,
# ...). Restore them, with the same result than before, so those plugins keep
# working with the Pillow version required by pibooth.
if not hasattr(ImageFont.FreeTypeFont, 'getsize'):
    ImageFont.FreeTypeFont.getsize = _font_getsize
if not hasattr(ImageDraw.ImageDraw, 'textsize'):
    ImageDraw.ImageDraw.textsize = _draw_textsize


def get_available_fonts():
    """Return the list of available fonts.
    """
    fonts_list = []
    for font_file in os.listdir(EMBEDDED_FONT_PATH):
        if fnmatch.fnmatch(font_file, '*.ttf'):
            fonts_list.append(osp.splitext(osp.basename(font_file))[0])

    fonts_list.extend(pygame.font.get_fonts())

    return sorted(fonts_list, key=lambda s: s.lower())


def get_filename(name):
    """Return absolute path to a font definition file located in the current
    package.
    """
    if osp.isfile(name):
        return name

    embedded_path = osp.join(osp.dirname(osp.abspath(__file__)), name)
    if embedded_path and osp.isfile(embedded_path):
        return embedded_path

    elif embedded_path and osp.isfile(embedded_path + '.ttf'):
        return embedded_path + '.ttf'

    system_path = pygame.font.match_font(name)
    if system_path and osp.isfile(system_path):
        return system_path

    # Show available fonts
    most_similar = None
    most_similar_ratio = 0
    for font_name in get_available_fonts():
        sim = SequenceMatcher(None, font_name, name).ratio()  # Similarity
        if sim > most_similar_ratio:
            most_similar = font_name
            most_similar_ratio = sim
    raise ValueError('System font "{0}" unknown, maybe you mean "{1}"'.format(name, most_similar))


def get_pil_font(text, font_name, max_width, max_height):
    """Create the PIL font object which fit the text to the given rectangle.

    :param text: text to draw
    :type text: str
    :param font_name: name or path to font definition file
    :type font_name: str
    :param max_width: width of the rect to fit
    :type max_width: int
    :param max_height: height of the rect to fit
    :type max_height: int

    :return: PIL.Font instance
    :rtype: object
    """
    start, end = 0, int(max_height * 2)
    while start < end:
        k = (start + end) // 2
        font = ImageFont.truetype(font_name, k)
        bbox = font.getbbox(text)
        font_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
        if font_size[0] > max_width or font_size[1] > max_height:
            end = k
        else:
            start = k + 1
    return ImageFont.truetype(font_name, start)


def get_pygame_font(text, font_name, max_width, max_height):
    """Create the pygame font object which fit the text to the given rectangle.

    :param text: text to draw
    :type text: str
    :param font_name: name or path to font definition file
    :type font_name: str
    :param max_width: width of the rect to fit
    :type max_width: int
    :param max_height: height of the rect to fit
    :type max_height: int

    :return: pygame.Font instance
    :rtype: object
    """
    start, end = 0, int(max_height * 2)
    while start < end:
        k = (start + end) // 2
        font = pygame.font.Font(get_filename(font_name), k)
        font_size = font.size(text)
        if font_size[0] > max_width or font_size[1] > max_height:
            end = k
        else:
            start = k + 1
        del font  # Run garbage collector, to avoid opening too many files
    return pygame.font.Font(get_filename(font_name), start)


CURRENT = get_filename('Amatic-Bold')  # Dynamically set at startup
