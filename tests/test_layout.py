# -*- coding: utf-8 -*-

"""Choice of the picture layout (template) after the captures."""

import os.path as osp
import pytest
from PIL import Image
from pibooth.view.background import LayoutBackground
from pibooth.view.window import PiWindow
from pibooth.plugins import create_plugin_manager, load_module
from pibooth.config.parser import PiConfigParser
from pibooth.pictures import get_picture_factory

ROOT = osp.dirname(osp.dirname(osp.abspath(__file__)))
PLUGIN = osp.join(ROOT, 'plugins', 'pibooth_picture_template.py')


@pytest.fixture
def previews():
    return [Image.new('RGB', (2400, 3600), color) for color in ('red', 'green', 'blue')]


@pytest.fixture
def window():
    return PiWindow("Test", (800, 480))


def test_layout_view_thumbnails_and_preview(init, window, previews):
    window.show_layout(previews, selected=1)
    bkgd = window._current_background  # pylint: disable=protected-access
    assert isinstance(bkgd, LayoutBackground)
    assert len(bkgd.thumbnails) == 3
    # Thumbnails in a row at the bottom, the preview above them
    rects = [rect for _, rect in bkgd.thumbnails]
    assert rects[0].right < rects[1].left < rects[2].left
    assert all(rect.bottom <= 480 for rect in rects)
    assert bkgd.preview_rect.bottom <= rects[0].top
    assert bkgd.preview_rect.width > rects[0].width


def test_layout_view_hit_test(init, window, previews):
    window.show_layout(previews, selected=0)
    bkgd = window._current_background  # pylint: disable=protected-access
    for index, (_, rect) in enumerate(bkgd.thumbnails):
        assert window.get_layout_index(rect.center) == index
    assert window.get_layout_index(bkgd.preview_rect.center) == -1
    assert window.get_layout_index((2, 2)) is None
    # Not on the layout view
    window.show_intro()
    assert window.get_layout_index(bkgd.preview_rect.center) is None


def test_layout_view_selection_changes(init, window, previews):
    window.show_layout(previews, selected=0)
    first = window._current_background  # pylint: disable=protected-access
    window.show_layout(previews, selected=2)
    assert window._current_background is not first  # pylint: disable=protected-access
    assert window._current_background.selected == 2  # pylint: disable=protected-access


@pytest.fixture(scope='module')  # The options can be declared only once
def template_cfg(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp('template')
    pm = create_plugin_manager()
    plugin = load_module(PLUGIN)
    pm.register(plugin, name='picture-template')
    cfg = PiConfigParser(str(tmpdir.join('pibooth.cfg')), pm)
    pm.hook.pibooth_configure(cfg=cfg)
    fancy = tmpdir.join('fancy.xml')
    fancy.write(open(osp.join(ROOT, 'tests', 'mocks', 'fancy.xml'), encoding='utf-8').read())
    cfg.set('PICTURE', 'template', '("{}", "{}")'.format(tmpdir.join('picture_template.xml'), fancy))
    pm.hook.pibooth_reset(cfg=cfg, hard=False)
    return pm, cfg


def test_plugin_declares_one_layout_per_template(template_cfg):
    pm, cfg = template_cfg
    # Both draw.io templates cover 1 and 4 captures
    assert pm.hook.pibooth_setup_layouts(cfg=cfg, capture_nbr=4) == ['picture_template', 'fancy']
    assert pm.hook.pibooth_setup_layouts(cfg=cfg, capture_nbr=1) == ['picture_template', 'fancy']
    assert osp.isfile(cfg.gettuple('PICTURE', 'template', 'path')[0])  # Default one generated


def test_plugin_builds_with_the_chosen_template(template_cfg, captures_portrait):
    pm, cfg = template_cfg
    pictures = []
    for layout_index in (0, 1):
        factory = pm.hook.pibooth_setup_picture_factory(cfg=cfg, opt_index=0,
                                                        factory=get_picture_factory(captures_portrait[:1]),
                                                        layout_index=layout_index)
        assert factory.template.filename == cfg.gettuple('PICTURE', 'template', 'path')[layout_index]
        pictures.append(factory.build())
    assert pictures[0].size == pictures[1].size == (2400, 3600)


def test_plugin_texts_are_drawn(template_cfg, captures_portrait):
    pm, cfg = template_cfg
    factory = pm.hook.pibooth_setup_picture_factory(cfg=cfg, opt_index=0,
                                                    factory=get_picture_factory(captures_portrait[:1]),
                                                    layout_index=0)
    factory.add_text("Hello", "Amatic-Bold", (255, 0, 0), 'center')
    picture = factory.build()
    # Red pixels of the text somewhere on the white background
    assert any(p[0] > 200 and p[1] < 80 and p[2] < 80 for p in picture.getdata())


@pytest.fixture(scope='module')
def json_template(tmpdir_factory):
    import json
    tmpdir = tmpdir_factory.mktemp('json')
    data = {
        "format": "pibooth-template", "version": 1, "name": "Masked", "captures": 2,
        "orientation": "portrait", "background": {"color": [250, 245, 235]},
        "slots": [
            {"type": "capture", "index": 1, "rect": [0.05, 0.05, 0.9, 0.4], "mask": "rounded", "radius": 0.05},
            {"type": "capture", "index": 2, "rect": [0.05, 0.5, 0.9, 0.4], "rotation": 5, "mask": "circle"},
            {"type": "text", "index": 1, "rect": [0.05, 0.92, 0.9, 0.06], "align": "center"},
        ],
    }
    path = tmpdir.join('masked.json')
    path.write(json.dumps(data))
    return str(path)


def test_json_template_is_a_layout_for_its_capture_count(template_cfg, json_template):
    pm, cfg = template_cfg
    cfg.set('PICTURE', 'template', '"{}"'.format(json_template))
    cfg.templates = {}  # Drop the cache of the draw.io templates
    assert pm.hook.pibooth_setup_layouts(cfg=cfg, capture_nbr=2) == ['masked']
    assert pm.hook.pibooth_setup_layouts(cfg=cfg, capture_nbr=4) == []  # Wrong count filtered out


def test_json_template_renders_masks_and_background(json_template, captures_portrait):
    import sys
    sys.path.insert(0, osp.join(ROOT, 'plugins'))
    import pibooth_picture_template as ppt
    template = ppt.JsonTemplate(json_template)
    assert template.available_counts() == {2}
    factory = template.build_factory('portrait', captures_portrait[:2])
    factory.add_text("Hello", "Amatic-Bold", (10, 10, 10), 'center')
    picture = factory.build()
    assert picture.size == (2400, 3600)
    # The background color shows in a corner (no capture there)
    assert picture.getpixel((5, 5))[:3] == (250, 245, 235)


def test_json_template_overlay_image_is_drawn(tmpdir, captures_portrait):
    import io
    import sys
    import json
    import base64
    sys.path.insert(0, osp.join(ROOT, 'plugins'))
    import pibooth_picture_template as ppt
    from PIL import Image
    # A fully magenta overlay square
    buf = io.BytesIO()
    Image.new('RGBA', (40, 40), (255, 0, 255, 255)).save(buf, 'PNG')
    src = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    data = {"format": "pibooth-template", "version": 1, "captures": 1, "orientation": "portrait",
            "background": {"color": [255, 255, 255]},
            "slots": [{"type": "capture", "index": 1, "rect": [0, 0, 1, 1]},
                      {"type": "image", "src": src, "rect": [0.4, 0.4, 0.2, 0.2]}]}
    path = tmpdir.join('overlay.json')
    path.write(json.dumps(data))
    factory = ppt.JsonTemplate(str(path)).build_factory('portrait', captures_portrait[:1])
    picture = factory.build()
    # Center is the magenta overlay, on top of the capture
    assert picture.getpixel((1200, 1800))[:3] == (255, 0, 255)
