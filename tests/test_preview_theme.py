# -*- coding: utf-8 -*-

"""Tests of tools/preview_theme.py (theme preview images)."""

import os.path as osp
import importlib.util

from PIL import Image

from pibooth import theme

ROOT = osp.dirname(osp.dirname(osp.abspath(__file__)))


def load_tool():
    spec = importlib.util.spec_from_file_location('preview_theme', osp.join(ROOT, 'tools', 'preview_theme.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_templates_rendered_at_print_size(tmpdir):
    tool = load_tool()
    written = tool.render_templates(theme.load('droidknights'), str(tmpdir))
    assert [osp.basename(path) for path in written] == ['droidknights-4.jpg', 'droidknights-1.jpg']
    for path in written:
        assert Image.open(path).size == (2400, 3600)
