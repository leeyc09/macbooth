# -*- coding: utf-8 -*-

"""Checks of the files maintained by hand next to the code."""

import re
import os.path as osp
from pibooth.language import DEFAULT

ROOT = osp.dirname(osp.dirname(osp.abspath(__file__)))


def test_translations_define_the_same_keys():
    reference = set(DEFAULT['en'])
    for code, texts in DEFAULT.items():
        assert set(texts) == reference, "language '{}'".format(code)


def test_languages_have_a_classifier():
    with open(osp.join(ROOT, 'setup.py'), encoding='utf-8') as fp:
        classifiers = re.findall(r"'Natural Language :: ", fp.read())
    assert len(classifiers) == len(DEFAULT)
