# -*- coding: utf-8 -*-

"""Tests of the pibooth admin server helpers (no HTTP needed)."""

import sys
import os.path as osp
import pytest

sys.path.insert(0, osp.dirname(osp.abspath(__file__)))
import pibooth_admin as admin  # noqa: E402


TEMPLATE = {
    "format": "pibooth-template", "version": 1, "name": "My Party", "captures": 4,
    "orientation": "portrait", "background": {"color": [244, 241, 234]},
    "slots": [
        {"type": "capture", "index": 1, "rect": [0.05, 0.05, 0.43, 0.31], "mask": "rounded", "radius": 0.05, "crop": True},
        {"type": "capture", "index": 2, "rect": [0.52, 0.05, 0.43, 0.31], "mask": "circle"},
        {"type": "capture", "index": 3, "rect": [0.05, 0.38, 0.43, 0.31]},
        {"type": "capture", "index": 4, "rect": [0.52, 0.38, 0.43, 0.31]},
        {"type": "text", "index": 1, "rect": [0.06, 0.76, 0.88, 0.1], "align": "center", "font": "Amatic-Bold", "color": [38, 34, 28]},
    ],
}


def test_slugify():
    assert admin.slugify("My Party!") == "my-party"
    assert admin.slugify("") == "template"
    assert admin.slugify("  A/B  c ") == "a-b-c"


def test_save_and_list_and_load(tmp_path):
    config = str(tmp_path)
    fname = admin.save_template(config, TEMPLATE)
    assert fname == "my-party.json"
    assert osp.isfile(osp.join(config, fname))

    listed = admin.list_templates(config)
    assert listed == [{"name": "My Party", "file": "my-party.json", "type": "json", "captures": 4}]

    loaded = admin.load_template(config, fname)
    assert loaded["name"] == "My Party" and len(loaded["slots"]) == 5


def test_save_rejects_non_template(tmp_path):
    with pytest.raises(ValueError):
        admin.save_template(str(tmp_path), {"foo": "bar"})


def test_load_rejects_unsafe_name(tmp_path):
    with pytest.raises(ValueError):
        admin.load_template(str(tmp_path), "../secret.json")


def test_list_ignores_non_templates(tmp_path):
    (tmp_path / "notes.json").write_text('{"hello": 1}')
    (tmp_path / "pibooth.cfg").write_text("[GENERAL]\n")
    assert admin.list_templates(str(tmp_path)) == []


def test_register_is_idempotent_and_merges(tmp_path):
    config = str(tmp_path)
    admin.save_template(config, TEMPLATE)
    first = admin.register_in_config(config, "my-party.json", plugin_path="/x/plugin.py")
    assert "my-party.json" in first["template"]
    assert first["plugins"] == '"/x/plugin.py"'

    # A second template: the tuple grows, no duplicates
    other = dict(TEMPLATE, name="Second")
    admin.save_template(config, other)
    second = admin.register_in_config(config, "second.json", plugin_path="/x/plugin.py")
    assert second["template"].count("my-party.json") == 1
    assert "second.json" in second["template"]
    assert second["template"].startswith("(") and second["template"].endswith(")")

    # Registering the same one again does not duplicate it
    again = admin.register_in_config(config, "second.json", plugin_path="/x/plugin.py")
    assert again["template"].count("second.json") == 1


def test_register_preserves_other_options(tmp_path):
    config = str(tmp_path)
    with open(osp.join(config, "pibooth.cfg"), "w", encoding="utf-8") as fp:
        fp.write("[WINDOW]\nsize = (800, 480)\n\n[PICTURE]\ntemplate = \"old.xml\"\n")
    admin.save_template(config, TEMPLATE)
    result = admin.register_in_config(config, "my-party.json", plugin_path="/x/plugin.py")
    assert "old.xml" in result["template"] and "my-party.json" in result["template"]
    with open(osp.join(config, "pibooth.cfg"), encoding="utf-8") as fp:
        content = fp.read()
    assert "size = (800, 480)" in content  # Untouched


def test_render_preview_returns_png(tmp_path):
    png = admin.render_preview(TEMPLATE, size=(300, 300))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 1000
