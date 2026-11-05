# -*- coding: utf-8 -*-

"""Compatibility of the fonts with the plugins written for Pillow < 10."""

from PIL import Image, ImageDraw, ImageFont
from pibooth import fonts


def test_font_getsize_is_the_bounding_box():
    font = ImageFont.truetype(fonts.get_filename('Amatic-Bold'), 40)
    _left, _top, right, bottom = font.getbbox("Hello")
    assert font.getsize("Hello") == (right, bottom)
    assert font.getsize("Hello", stroke_width=2) == font.getbbox("Hello", stroke_width=2)[2:]


def test_draw_textsize_is_the_bounding_box():
    font = ImageFont.truetype(fonts.get_filename('Amatic-Bold'), 40)
    draw = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    _left, _top, right, bottom = draw.textbbox((0, 0), "Hello", font)
    assert draw.textsize("Hello", font) == (right, bottom)
    assert draw.textsize("Hello", font=font) == (right, bottom)
