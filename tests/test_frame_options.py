# -*- coding: utf-8 -*-

"""Tests of the frame options of the picture template plugin: fixed frames
(the choice is skipped) and excluded frames."""

import sys
import json
import configparser
import os.path as osp
import pytest

sys.path.insert(0, osp.join(osp.dirname(osp.dirname(osp.abspath(__file__))), 'plugins'))
import pibooth_picture_template as ppt  # noqa: E402
from pibooth import theme  # noqa: E402


class Cfg(object):
    def __init__(self, paths, fixed=(), excluded=()):
        self.values = {'template': paths, 'frames_fixed': fixed, 'frames_excluded': excluded}

    def gettuple(self, section, option, types, extend=0):
        if option not in self.values:
            raise configparser.NoOptionError(option, section)
        return tuple(self.values[option])

    def get(self, section, option):
        return 'auto'


@pytest.fixture
def templates(tmp_path, monkeypatch):
    monkeypatch.setattr(theme, 'CURRENT', theme.EMPTY)       # Use the [PICTURE] template option
    paths = []
    for name, captures in (('grid', 4), ('polaroid', 4), ('strip', 4), ('solo', 1)):
        path = tmp_path / (name + '.json')
        path.write_text(json.dumps({'format': 'pibooth-template', 'version': 1, 'captures': captures,
                                    'orientation': 'portrait', 'slots': []}))
        paths.append(str(path))
    return paths


def names(cfg, captures):
    return ppt.pibooth_setup_layouts(cfg, captures)


def test_all_frames_offered_by_default(templates):
    assert names(Cfg(templates), 4) == ['grid', 'polaroid', 'strip']
    assert names(Cfg(templates), 1) == ['solo']


def test_excluded_frames_are_not_offered(templates):
    assert names(Cfg(templates, excluded=['polaroid', 'strip']), 4) == ['grid']


def test_fixed_frame_skips_the_choice(templates):
    cfg = Cfg(templates, fixed=['strip', 'solo'])           # One per number of captures
    assert names(cfg, 4) == ['strip']
    assert names(cfg, 1) == ['solo']
    # Unknown or excluded fixed frame: back to the choice among the others
    assert names(Cfg(templates, fixed=['nope']), 4) == ['grid', 'polaroid', 'strip']
    assert names(Cfg(templates, fixed=['strip'], excluded=['strip']), 4) == ['grid', 'polaroid']


def test_options_not_declared(templates):
    cfg = Cfg(templates)
    del cfg.values['frames_fixed'], cfg.values['frames_excluded']
    assert names(cfg, 4) == ['grid', 'polaroid', 'strip']
