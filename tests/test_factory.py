# -*- coding: utf-8 -*-

"""Tests of the photo factory page server (pictures in a local folder)."""

import io
import os
import sys
import json
import os.path as osp
from urllib.request import urlopen
from urllib.error import HTTPError

import pytest
from PIL import Image

sys.path.insert(0, osp.join(osp.dirname(osp.dirname(osp.abspath(__file__))), 'plugins'))
import pibooth_factory as factory  # noqa: E402


def picture(tmp_path, name, size=(2400, 3600)):
    path = tmp_path / name
    Image.new('RGB', size, (200, 30, 60)).save(str(path))
    return str(path)


def touch(path, seconds):
    """Give a file a precise modification time (the order of the list)."""
    os.utime(path, (seconds, seconds))


@pytest.fixture
def folder(tmp_path):
    return factory.PhotoFolder(str(tmp_path / 'factory'), keep=3)


@pytest.fixture
def server(folder):
    srv = factory.start_server(folder, '127.0.0.1', 0)
    yield folder, 'http://127.0.0.1:{}/'.format(srv.server_address[1])
    srv.shutdown()
    srv.server_close()


def get_json(url):
    with urlopen(url) as res:
        return json.loads(res.read())


def test_page_is_served(server):
    _, base = server
    with urlopen(base) as res:
        assert b'Photo Factory' in res.read()
    with urlopen(base + 'assets/logo-lockup.png') as res:
        assert res.headers['Content-Type'] == 'image/png'


def test_added_pictures_are_resized_copies(folder, tmp_path):
    original = picture(tmp_path, '2026-10-16-18-00-00_pibooth.jpg')
    name = folder.add(original)
    assert name == '2026-10-16-18-00-00_pibooth.jpg'
    with Image.open(osp.join(folder.path, name)) as image:
        assert image.size == (900, 1350)
    assert osp.isfile(original)                                  # The original is kept


def test_only_the_newest_pictures_are_kept(folder, tmp_path):
    originals = [picture(tmp_path, 'p{}.jpg'.format(i), (30, 45)) for i in range(5)]
    for i, original in enumerate(originals):
        folder.add(original)
        touch(osp.join(folder.path, 'p{}.jpg'.format(i)), 1000 + i)
    folder.prune()
    assert sorted(os.listdir(folder.path)) == ['p2.jpg', 'p3.jpg', 'p4.jpg']
    assert all(osp.isfile(o) for o in originals)                 # Originals never deleted


def test_list_follows_the_folder(server, tmp_path):
    folder, base = server
    folder.add(picture(tmp_path, 'old.jpg', (30, 45)))
    touch(osp.join(folder.path, 'old.jpg'), 1000)
    first = get_json(base + 'api/photos?after=-1')
    assert first == {'latest': 1000 * 10**6, 'photos': []}        # Page opened: nothing replayed

    # A picture put in the folder by any mean is listed
    Image.new('RGB', (30, 45)).save(osp.join(folder.path, 'dropped.jpg'))
    touch(osp.join(folder.path, 'dropped.jpg'), 2000)
    data = get_json(base + 'api/photos?after={}'.format(first['latest']))
    assert [p['url'] for p in data['photos']] == ['photos/dropped.jpg']
    assert data['latest'] == 2000 * 10**6
    assert get_json(base + 'api/photos?after={}'.format(data['latest']))['photos'] == []


def test_pictures_are_served_and_names_checked(server, tmp_path):
    folder, base = server
    name = folder.add(picture(tmp_path, 'p.jpg'))
    with urlopen(base + 'photos/' + name) as res:
        assert res.headers['Content-Type'] == 'image/jpeg'
        assert Image.open(io.BytesIO(res.read())).size == (900, 1350)
    for path in ('photos/missing.jpg', 'photos/..%2Fsecret.jpg', 'photos/.hidden.jpg', 'photos/p.txt'):
        with pytest.raises(HTTPError) as err:
            urlopen(base + path)
        assert err.value.code == 404


class App(object):
    pass


def test_processing_exit_publishes_the_final_picture(folder, tmp_path, monkeypatch):
    monkeypatch.setattr(factory, '_FOLDER', folder)
    app = App()
    app.previous_picture_file = picture(tmp_path, 'final.jpg', (30, 45))
    factory.state_processing_exit(app)
    assert os.listdir(folder.path) == ['final.jpg']
    app.previous_picture_file = str(tmp_path / 'missing.jpg')
    factory.state_processing_exit(app)                          # Nothing, no error
    assert os.listdir(folder.path) == ['final.jpg']


class SettingsCfg(object):
    """Minimal pibooth configuration (values stored as their text)."""

    def __init__(self):
        self.values = {('GENERAL', 'theme'): 'droidknights', ('GENERAL', 'language'): 'ko',
                       ('PICTURE', 'captures'): '(4, 1)', ('PICTURE', 'frames_fixed'): '',
                       ('PICTURE', 'frames_excluded'): '', ('PICTURE', 'template'): '',
                       ('WINDOW', 'preview_delay'): '3', ('WINDOW', 'flash'): 'True',
                       ('FACTORY', 'keep'): '50'}
        self.saved = 0

    def has_option(self, section, option):
        return (section, option) in self.values

    def get(self, section, option):
        # Like pibooth: the default value when the option is not in the file
        from pibooth.config.parser import DEFAULT
        if (section, option) in self.values:
            return self.values[(section, option)]
        return str(DEFAULT[section][option][0])

    def set(self, section, option, value):
        self.values[(section, option)] = value

    def save(self):
        self.saved += 1

    def _typed(self, section, option):
        import ast
        try:
            return ast.literal_eval(self.get(section, option))
        except (ValueError, SyntaxError):
            return self.get(section, option)

    def gettuple(self, section, option, types, extend=0):
        value = self._typed(section, option)
        if value == '':
            return ()
        return tuple(value) if isinstance(value, (tuple, list)) else (value,)

    def getboolean(self, section, option):
        return self.get(section, option) == 'True'

    def getint(self, section, option):
        return int(self.get(section, option))

    def getfloat(self, section, option):
        return float(self.get(section, option))


def field(groups, key):
    return next(f for g in groups for f in g['fields'] if f['key'] == key)


def test_settings_describe_only_declared_options():
    groups = factory.Settings(SettingsCfg()).describe()
    keys = [f['key'] for g in groups for f in g['fields']]
    assert 'PICTURE.captures' in keys and 'FACTORY.keep' in keys
    assert 'R2.keep_local' not in keys                     # R2 plugin not loaded
    assert field(groups, 'PICTURE.captures')['value'] == [4, 1]
    assert 'droidknights' in [c['value'] for c in field(groups, 'GENERAL.theme')['choices']]
    frames = [c['value'] for c in field(groups, 'PICTURE.frames_fixed')['choices']]
    assert frames == ['droidknights-4', 'droidknights-1'] or frames == []   # Depends on the current theme


def test_settings_update_writes_and_reports():
    cfg, changes = SettingsCfg(), []
    settings = factory.Settings(cfg, changes.append)
    result = settings.update({'PICTURE.captures': [4], 'WINDOW.preview_delay': 5, 'WINDOW.flash': False,
                              'FACTORY.keep': 50})
    assert cfg.values[('PICTURE', 'captures')] == '(4,)'
    assert cfg.values[('WINDOW', 'preview_delay')] == '5'
    assert cfg.values[('WINDOW', 'flash')] == 'False'
    assert cfg.saved == 1
    assert sorted(result['changed']) == sorted(['컷 수', '카운트다운 (초)', '촬영 플래시'])   # keep unchanged
    assert result['restart'] == []
    assert changes == [[('PICTURE', 'captures'), ('WINDOW', 'preview_delay'), ('WINDOW', 'flash')]]
    assert settings.update({'WINDOW.flash': False})['changed'] == []          # Nothing new: not saved
    assert cfg.saved == 1


@pytest.mark.parametrize('values', [
    {'PICTURE.captures': []},                 # At least one
    {'PICTURE.captures': [5]},                # Unknown choice
    {'WINDOW.preview_delay': 60},             # Out of range
    {'WINDOW.preview_delay': 'abc'},
    {'GENERAL.theme': 'nope'},
    {'R2.keep_local': 10},                    # Not declared
])
def test_settings_update_rejects_invalid_values(values):
    cfg = SettingsCfg()
    before = dict(cfg.values)
    with pytest.raises(factory.SettingsError):
        factory.Settings(cfg).update(values)
    assert cfg.values == before and cfg.saved == 0


def test_settings_api_and_pin(folder):
    cfg = SettingsCfg()
    srv = factory.start_server(folder, '127.0.0.1', 0, settings=factory.Settings(cfg), pin='1234')
    base = 'http://127.0.0.1:{}/'.format(srv.server_address[1])
    try:
        from urllib.request import Request
        with urlopen(base + 'settings') as res:                        # The page
            assert '설정'.encode('utf-8') in res.read()
        assert get_json(base + 'api/settings') == {'groups': [], 'pin': True, 'authorized': False}
        req = Request(base + 'api/settings', headers={'X-Settings-Pin': '1234'})
        with urlopen(req) as res:
            assert json.loads(res.read())['authorized'] is True

        def post(values, pin):
            req = Request(base + 'api/settings', data=json.dumps({'values': values}).encode(), method='POST',
                          headers={'Content-Type': 'application/json', 'X-Settings-Pin': pin})
            with urlopen(req) as res:
                return json.loads(res.read())
        with pytest.raises(HTTPError) as err:
            post({'WINDOW.preview_delay': 4}, 'wrong')
        assert err.value.code == 403
        assert post({'WINDOW.preview_delay': 4}, '1234')['changed'] == ['카운트다운 (초)']
        with pytest.raises(HTTPError) as err:
            post({'WINDOW.preview_delay': 99}, '1234')
        assert err.value.code == 400 and '1~10' in json.loads(err.value.read())['error']
    finally:
        srv.shutdown()
        srv.server_close()


class FakeMachine(object):
    def __init__(self, state):
        self.active_state = state


class FakeBooth(object):
    def __init__(self, state, captures=(4, 1)):
        self._machine = FakeMachine(state)
        self.capture_choices = captures
        self.capture_nbr = None
        self.layout_choices = ()
        self.layout_nbr = 0
        self.layout_previews = None
        self.previous_picture = None


@pytest.fixture
def remote(monkeypatch):
    remote = factory.Remote()
    monkeypatch.setattr(factory, '_REMOTE', remote)
    posted = []
    monkeypatch.setattr(factory, 'key_event', posted.append)
    return remote, posted


def test_remote_start_with_captures_choice(remote):
    import pygame
    remote, posted = remote
    app = remote.app = FakeBooth('wait')
    assert remote.state()['captures'] == [4, 1]
    remote.request('start', 1)
    with pytest.raises(factory.RemoteError):
        remote.request('start', 4)                     # One request at a time
    factory.state_wait_do(app, None, [])
    assert posted == [pygame.K_p]                       # Same as the booth keyboard
    app._machine.active_state = 'choose'
    factory.state_choose_do(app)
    assert posted == [pygame.K_p, pygame.K_RIGHT]       # 1 is the second choice
    factory.state_choose_do(app)
    assert len(posted) == 2                             # Done once


def test_remote_rejects_actions_out_of_state(remote):
    remote, _ = remote
    remote.app = FakeBooth('preview')
    with pytest.raises(factory.RemoteError, match='촬영 중'):
        remote.request('start', 4)
    remote.app = FakeBooth('wait')
    for action, value in (('start', 3), ('nope', None), ('choose', 4)):
        with pytest.raises(factory.RemoteError):
            remote.request(action, value)


def test_remote_frames(remote):
    import pygame
    from PIL import Image
    remote, posted = remote
    app = remote.app = FakeBooth('layout')
    app.layout_choices = ('grid', 'polaroid')
    app.layout_previews = [Image.new('RGB', (1200, 1800), (200, 0, 0)), Image.new('RGB', (1200, 1800))]
    state = remote.state()
    assert state['layouts'] == ['grid', 'polaroid'] and state['previews'] == 2
    thumb = remote.layout_preview(1)
    assert Image.open(io.BytesIO(thumb)).size == (600, 900)
    remote.request('layout', 1)
    factory.state_layout_do(app)
    assert app.layout_nbr == 1 and posted == []         # Selected directly
    remote.request('layout', 'validate')
    factory.state_layout_do(app)
    assert posted == [pygame.K_RETURN]
    with pytest.raises(factory.RemoteError):
        remote.request('layout', 5)


def test_remote_qr_of_the_last_picture(remote):
    remote, _ = remote
    app = remote.app = FakeBooth('wait')
    assert remote.qr_png() is None
    app.previous_picture, app.previous_qr_url = object(), 'https://photo.example.com/p/abc.jpg'
    assert remote.state()['qr'] == 'https://photo.example.com/p/abc.jpg'
    assert remote.qr_png()[:4] == b'\x89PNG'


def test_remote_reset_clears_the_last_picture(remote):
    class Win(object):
        shown = 'picture'

        def show_intro(self, picture, with_print):
            self.shown = picture

    class Printer(object):
        def is_ready(self):
            return False

    remote, posted = remote
    app = remote.app = FakeBooth('wait')
    app.printer, app.count = Printer(), None
    app.previous_picture, app.previous_qr_url, app.previous_qr_base = object(), 'https://x/p/a.jpg', object()
    app.previous_animated = None
    assert remote.state()['picture']
    remote.request('reset')
    win = Win()
    factory.state_wait_do(app, win, [])
    assert posted == [] and win.shown is None
    assert app.previous_picture is None and app.previous_qr_url is None and app.previous_qr_base is None
    state = remote.state()
    assert 'picture' not in state and 'qr' not in state
    remote.app = FakeBooth('preview')
    with pytest.raises(factory.RemoteError):
        remote.request('reset')


def test_remote_api(folder, remote):
    remote, posted = remote
    remote.app = FakeBooth('wait', captures=(4,))
    srv = factory.start_server(folder, '127.0.0.1', 0, remote=remote)
    base = 'http://127.0.0.1:{}/'.format(srv.server_address[1])
    try:
        from urllib.request import Request
        with urlopen(base + 'remote') as res:
            assert b'MacBooth Remote' in res.read()
        assert get_json(base + 'api/remote')['state'] == 'wait'
        req = Request(base + 'api/remote', data=json.dumps({'action': 'start'}).encode(), method='POST',
                      headers={'Content-Type': 'application/json'})
        with urlopen(req) as res:
            assert json.loads(res.read()) == {'ok': True}
        assert get_json(base + 'api/remote')['busy'] is True
        with pytest.raises(HTTPError) as err:
            urlopen(Request(base + 'api/remote', data=b'{"action": "start"}', method='POST'))
        assert err.value.code == 409
    finally:
        srv.shutdown()
        srv.server_close()


def test_server_base(monkeypatch):
    monkeypatch.setattr(factory, 'lan_address', lambda: '192.168.0.7')
    assert factory.server_base('0.0.0.0', 8770) == ('http://192.168.0.7:8770', True)
    assert factory.server_base('127.0.0.1', 8770) == ('http://localhost:8770', False)
    assert factory.server_base('10.0.0.2', 80) == ('http://10.0.0.2:80', True)
    monkeypatch.setattr(factory, 'lan_address', lambda: None)
    assert factory.server_base('0.0.0.0', 8770) == ('http://localhost:8770', False)


def test_address_panel_toggle():
    panel = factory.AddressPanel('http://localhost:8770', False)
    assert panel.is_visible()                 # Shown after the start
    urls = [url for _, url in panel.lines()]
    assert urls[1:] == ['http://localhost:8770/settings', 'http://localhost:8770/remote']
    assert panel.toggle() is True             # I: hide
    assert not panel.is_visible()
    assert panel.toggle() is False            # I: show until the next I
    panel.shown_until = 0
    assert panel.is_visible()
