# -*- coding: utf-8 -*-

"""Tests of the theme system (pibooth.theme) and of its consumers."""

import json
import os.path as osp
import pytest

from pibooth import theme, language, fonts


@pytest.fixture
def droidknights():
    previous = theme.CURRENT
    theme.CURRENT = theme.load('droidknights')
    yield theme.CURRENT
    theme.CURRENT = previous


def test_available_themes():
    assert {'classic', 'droidknights'} <= set(theme.get_available())


def test_to_rgb():
    assert theme.to_rgb('#2D7BFF') == (45, 123, 255)
    assert theme.to_rgb('fff') == (255, 255, 255)
    assert theme.to_rgb([1, 2, 3, 4]) == (1, 2, 3)
    with pytest.raises(ValueError):
        theme.to_rgb('#12')


def test_empty_theme_returns_defaults():
    empty = theme.load('')
    assert not empty
    assert empty.color('accent', (1, 2, 3)) == (1, 2, 3)
    assert empty.role_color('booth', 'flash', (255, 255, 255)) == (255, 255, 255)
    assert empty.font('display', 'Amatic-Bold') == 'Amatic-Bold'
    assert empty.text('intro', 'ko') is None
    assert empty.templates() == []


def test_unknown_theme_is_empty(caplog):
    assert not theme.load('does-not-exist')
    assert "not found" in caplog.text


def test_theme_from_folder_path():
    folder = osp.join(theme.THEMES_DIR, 'classic')
    assert theme.load(folder).name == 'Classic'


def test_colors_and_aliases(droidknights):
    assert droidknights.color('background') == (11, 18, 48)          # alias -> space
    assert droidknights.color('accent') == droidknights.color('blue')
    assert droidknights.color('#FF0000') == (255, 0, 0)
    assert droidknights.color('unknown') is None
    assert droidknights.role_color('booth', 'pictogram') == droidknights.color('lavender')
    assert droidknights.role_color('qrcode', 'background') == (255, 255, 255)


def test_fonts_and_assets_exist(droidknights):
    for token in ('display', 'heading', 'body', 'mono'):  # theme files or shared pibooth fonts
        assert osp.isfile(fonts.get_filename(droidknights.font(token))), token
    assert osp.isfile(fonts.get_filename(droidknights.role_font('booth', 'font')))
    for name in ('logo', 'icon', 'mascot', 'booth_background'):
        assert osp.isfile(droidknights.asset(name)), name
    assert droidknights.role_asset('booth', 'background_image') == droidknights.asset('booth_background')


def test_font_name_is_kept_when_not_a_file():
    classic = theme.load('classic')
    assert classic.font('display') == 'Amatic-Bold'
    assert classic.role_font('booth', 'font_ko') == 'NotoSansKR-Bold'  # Hangul glyphs
    assert classic.role_font('booth', 'font_fr') is None


def test_texts(droidknights):
    assert droidknights.text('intro', 'ko') == "사진 찍기"
    assert droidknights.text('qrcode', 'fr') == droidknights.text('qrcode', 'en')  # fallback
    assert droidknights.text('intro', 'fr', fallback=False) is None


def test_templates_are_valid(droidknights):
    paths = droidknights.templates()
    assert len(paths) == 2
    for path in paths:
        with open(path, encoding='utf-8') as fp:
            data = json.load(fp)
        assert data['format'] == 'pibooth-template'
        assert data['captures'] in (1, 4)
        assert data['background']['image'].startswith('data:image/jpeg;base64,')
    assert len(theme.load('classic').templates()) == 4


def test_translation_uses_theme_texts(tmpdir, droidknights):
    language.init(str(tmpdir.join('translations.cfg')))
    previous = language.CURRENT
    try:
        language.CURRENT = 'ko'
        assert language.get_translated_text('finished') == droidknights.text('finished', 'ko')
        language.CURRENT = 'fr'  # Not in the theme: the translations file is used
        assert language.get_translated_text('intro') == language.DEFAULT['fr']['intro']
    finally:
        language.CURRENT = previous


def test_korean_translations_are_complete():
    assert set(language.DEFAULT['ko']) == set(language.DEFAULT['en'])


def test_template_text_slot_style_is_used(tmpdir, droidknights):
    """The font (name or theme token) and color of a text slot win over the
    [PICTURE] options."""
    import sys
    sys.path.insert(0, osp.join(osp.dirname(osp.dirname(osp.abspath(__file__))), 'plugins'))
    import pibooth_picture_template as ppt
    from PIL import Image

    data = {"format": "pibooth-template", "version": 1, "captures": 1, "orientation": "portrait",
            "background": {"color": [0, 0, 0]},
            "slots": [{"type": "capture", "rect": [0, 0, 1, 0.5], "index": 1},
                      {"type": "text", "rect": [0, 0.6, 1, 0.2], "index": 1, "font": "Amatic-Bold", "color": "accent"},
                      {"type": "text", "rect": [0, 0.8, 1, 0.2], "index": 2, "font": "display", "color": [0, 255, 0]}]}
    path = tmpdir.join('t.json')
    path.write(json.dumps(data))
    factory = ppt.JsonTemplate(str(path)).build_factory('portrait', [Image.new('RGB', (40, 30), (9, 9, 9))])
    factory.add_text("HELLO", "Amatic-Bold", (255, 255, 255), 'center')
    factory.add_text("WORLD", "Amatic-Bold", (255, 255, 255), 'center')
    picture = factory.build()
    width, height = picture.size
    top = picture.crop((0, int(height * 0.6), width, int(height * 0.8))).getcolors(1 << 20)
    bottom = picture.crop((0, int(height * 0.8), width, height)).getcolors(1 << 20)
    assert any(color == droidknights.color('accent') for _, color in top)
    assert any(color == (0, 255, 0) for _, color in bottom)
    assert not any(color == (255, 255, 255) for _, color in top + bottom)
