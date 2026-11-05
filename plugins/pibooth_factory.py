# -*- coding: utf-8 -*-

"""Pibooth plugin serving the "photo factory" display page on the local network.

The page (``factory/index.html`` of this repository) shows each new picture of
the booth going through an animated factory. It is served by a small HTTP
server started with pibooth, with the pictures read from the local disk (no
upload needed, works offline).

The list of pictures is a folder (``photos_dir``, by default ``factory/`` in
the pibooth pictures directory): each final picture is copied there resized
for the screen, and only the ``keep`` newest files are kept (the older ones
are deleted, the original pictures of pibooth are never touched). Any JPEG
put in this folder is shown, the list is not held in memory.

- ``GET /``                         the factory page and its assets
- ``GET /api/photos?after=<time>``  ``{"latest": time, "photos": [{"name", "url", "time"}]}``
  with the times in microseconds (``after=-1`` only returns the latest time:
  the page shows the pictures added from its opening)
- ``GET /photos/<name>.jpg``        a picture of the folder

Open ``http://localhost:8770/`` in a browser (full screen) on the booth, or on
another computer of the network with ``host = 0.0.0.0``. Options of the
``[FACTORY]`` section: ``enabled``, ``host``, ``port``, ``photos_dir``,
``keep``, ``directory`` (folder of the page, empty for the one of the repository).
"""

import io
import os
import re
import json
import time
import socket
import threading
import os.path as osp
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from PIL import Image

import pibooth
from pibooth.utils import LOGGER

__version__ = "1.1.0"

SECTION = 'FACTORY'
PAGE_DIR = osp.join(osp.dirname(osp.dirname(osp.abspath(__file__))), 'factory')
SCREEN_SIZE = (900, 1350)   # Enough for the page, light for the browser (WebGL textures)
NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*\.jpe?g$', re.IGNORECASE)


class PhotoFolder(object):

    """The pictures of the page: the JPEG files of a folder, ordered by time."""

    def __init__(self, path, keep=50):
        self.path = path
        self.keep = keep
        self._lock = threading.Lock()   # Serialize the writes and the pruning
        os.makedirs(path, exist_ok=True)

    def _entries(self):
        """Return the (time in us, name) of the pictures, oldest first."""
        entries = []
        for name in os.listdir(self.path):
            if NAME_RE.match(name):
                try:
                    entries.append((os.stat(osp.join(self.path, name)).st_mtime_ns // 1000, name))
                except OSError:
                    continue  # Deleted meanwhile
        return sorted(entries)

    def add(self, picture):
        """Copy a picture resized for the screen, then delete the oldest ones
        over the ``keep`` limit. Return the name of the copy.
        """
        name = osp.splitext(osp.basename(picture))[0] + '.jpg'
        image = Image.open(picture).convert('RGB')
        image.thumbnail(SCREEN_SIZE, Image.LANCZOS)
        with self._lock:
            tmp = osp.join(self.path, '.' + name + '.tmp')
            image.save(tmp, 'JPEG', quality=88)
            os.replace(tmp, osp.join(self.path, name))  # Never listed half written
            self.prune()
        return name

    def prune(self):
        """Delete the oldest pictures over the ``keep`` limit."""
        entries = self._entries()
        for _, name in entries[:max(0, len(entries) - self.keep)]:
            try:
                os.remove(osp.join(self.path, name))
            except OSError:
                pass

    def after(self, time_us):
        """Return the latest time and the (time, name) of the pictures newer
        than the given time (only the latest time if it is negative).
        """
        entries = self._entries()
        latest = entries[-1][0] if entries else 0
        if time_us < 0:
            return latest, []
        return latest, [entry for entry in entries if entry[0] > time_us]

    def file(self, name):
        """Return the path of a picture of the folder, or None."""
        if not NAME_RE.match(name):
            return None
        path = osp.join(self.path, name)
        return path if osp.isfile(path) else None


# --- Settings page ------------------------------------------------------------
# Field: (group, section, option, label, kind, extra, live). 'live' fields are
# applied to the running booth at the next wait screen, the other ones after a
# restart of pibooth.
def _theme_choices(cfg):
    from pibooth import theme  # pylint: disable=import-outside-toplevel
    return [('', '없음 (설정값 사용)')] + [(name, name) for name in theme.get_available()]


def _language_choices(cfg):
    from pibooth import language  # pylint: disable=import-outside-toplevel
    return [(lang, lang) for lang in language.get_supported_languages()]


def _frame_choices(cfg):
    from pibooth import theme  # pylint: disable=import-outside-toplevel
    paths = theme.CURRENT.templates()
    if not paths:
        try:
            paths = [p for p in cfg.gettuple('PICTURE', 'template', 'path') if p]
        except Exception:  # pylint: disable=broad-except
            paths = []
    names = [osp.splitext(osp.basename(path))[0] for path in paths]
    return [(name, name) for name in names]


CAPTURE_CHOICES = [(4, '4컷'), (3, '3컷'), (2, '2컷'), (1, '1컷')]

FIELDS = [
    ('기본', 'GENERAL', 'theme', '테마', 'select', {'choices': _theme_choices}, True),
    ('기본', 'GENERAL', 'language', '언어', 'select', {'choices': _language_choices}, True),
    ('촬영', 'PICTURE', 'captures', '컷 수', 'multi_int',
     {'choices': CAPTURE_CHOICES, 'help': '하나만 고르면 선택 화면 없이 그 컷 수로 찍습니다'}, True),
    ('촬영', 'PICTURE', 'frames_fixed', '고정 프레임', 'multi',
     {'choices': _frame_choices, 'help': '컷 수마다 고른 프레임으로 바로 만들고 프레임 선택을 건너뜁니다'}, True),
    ('촬영', 'PICTURE', 'frames_excluded', '제외할 프레임', 'multi',
     {'choices': _frame_choices, 'help': '선택지에 나오지 않습니다'}, True),
    ('촬영', 'WINDOW', 'preview_delay', '카운트다운 (초)', 'int', {'min': 1, 'max': 10}, True),
    ('촬영', 'WINDOW', 'preview_countdown', '카운트다운 숫자 표시', 'bool', {}, True),
    ('촬영', 'WINDOW', 'flash', '촬영 플래시', 'bool', {}, True),
    ('촬영', 'WINDOW', 'layout_delay', '프레임 선택 대기 (초)', 'int',
     {'min': 0, 'max': 120, 'help': '0이면 프레임 선택 화면을 건너뜁니다'}, True),
    ('카메라', 'CAMERA', 'opencv_camera', '사용할 카메라', 'text',
     {'help': "ask: 시작할 때 선택 / 카메라 이름 일부 (예: MacBook) / 번호"}, False),
    ('QR', 'QRCODE', 'size', 'QR 크기 (720px 화면 기준)', 'int', {'min': 100, 'max': 600}, True),
    ('업로드', 'R2', 'keep_local', '맥에 남길 회차 수', 'int',
     {'min': 0, 'max': 100000, 'help': '업로드가 끝난 회차만 오래된 것부터 지웁니다. 0이면 지우지 않습니다'}, False),
    ('업로드', 'R2', 'upload_raw', '원본 컷 업로드', 'bool', {}, False),
    ('업로드', 'R2', 'random_names', '무작위 파일 이름', 'bool', {}, False),
    ('영상', 'CLIP', 'enabled', '촬영 영상 만들기', 'bool', {}, False),
    ('영상', 'CLIP', 'seconds', '컷마다 영상 길이 (초)', 'float', {'min': 0.5, 'max': 5}, False),
    ('영상', 'CLIP', 'single_seconds', '1컷일 때 영상 길이 (초)', 'float',
     {'min': 0.5, 'max': 10, 'help': '카운트다운 시간보다 길게 찍히지는 않습니다'}, True),
    ('사진 공장', 'FACTORY', 'keep', '공장 화면용 사진 보관 수', 'int', {'min': 5, 'max': 1000}, True),
    ('연결', 'FACTORY', 'host', '접속 허용', 'select',
     {'choices': [('127.0.0.1', '이 맥에서만'), ('0.0.0.0', '같은 네트워크 (아이패드 리모컨)')],
      'help': '아이패드 리모컨을 쓰려면 같은 네트워크로 바꾸세요'}, False),
    ('연결', 'FACTORY', 'settings_pin', '설정 화면 PIN', 'text',
     {'help': '같은 네트워크에 열 때는 PIN을 정하세요 (비우면 PIN 없음). 리모컨에는 필요 없습니다'}, False),
]


class SettingsError(ValueError):
    pass


class Settings(object):

    """Read and write the booth options of the settings page."""

    def __init__(self, cfg, on_change=None):
        self.cfg = cfg
        self.on_change = on_change
        self._lock = threading.Lock()

    def _declared(self, section, option):
        """True if the option is declared (by pibooth or a loaded plugin), even
        if it is not written in the configuration file yet."""
        from pibooth.config.parser import DEFAULT  # pylint: disable=import-outside-toplevel
        return option in DEFAULT.get(section, {}) or self.cfg.has_option(section, option)

    def _fields(self):
        for group, section, option, label, kind, extra, live in FIELDS:
            if self._declared(section, option):
                yield group, section, option, label, kind, extra, live

    def _choices(self, extra):
        choices = extra.get('choices', [])
        return choices(self.cfg) if callable(choices) else choices

    def _value(self, section, option, kind):
        if kind == 'multi_int':
            return [int(v) for v in self.cfg.gettuple(section, option, int)]
        if kind == 'multi':
            return [str(v) for v in self.cfg.gettuple(section, option, str) if v]
        if kind == 'bool':
            return self.cfg.getboolean(section, option)
        if kind == 'int':
            return self.cfg.getint(section, option)
        if kind == 'float':
            return self.cfg.getfloat(section, option)
        return str(self.cfg.get(section, option))

    def describe(self):
        """Return the groups of fields with their current values (page data)."""
        groups = []
        for group, section, option, label, kind, extra, live in self._fields():
            if not groups or groups[-1]['title'] != group:
                groups.append({'title': group, 'fields': []})
            field = {'key': section + '.' + option, 'label': label, 'kind': kind, 'live': live,
                     'value': self._value(section, option, kind), 'help': extra.get('help', '')}
            for name in ('min', 'max'):
                if name in extra:
                    field[name] = extra[name]
            if 'choices' in extra:
                field['choices'] = [{'value': v, 'label': lbl} for v, lbl in self._choices(extra)]
            groups[-1]['fields'].append(field)
        return groups

    def _serialize(self, kind, value, extra, label):
        """Return the configuration string of a value, or raise SettingsError."""
        if kind in ('multi', 'multi_int'):
            if not isinstance(value, list):
                raise SettingsError("{}: 목록이어야 합니다".format(label))
            allowed = [v for v, _ in self._choices(extra)]
            if kind == 'multi_int':
                value = [int(v) for v in value]
                if not value:
                    raise SettingsError("{}: 하나 이상 골라야 합니다".format(label))
            if any(v not in allowed for v in value):
                raise SettingsError("{}: 알 수 없는 값".format(label))
            if kind == 'multi_int':
                return str(tuple(value))
            return ', '.join('"{}"'.format(v) for v in value)
        if kind == 'bool':
            return 'True' if bool(value) else 'False'
        if kind in ('int', 'float'):
            try:
                number = int(value) if kind == 'int' else float(value)
            except (TypeError, ValueError):
                raise SettingsError("{}: 숫자를 입력하세요".format(label)) from None
            if not extra.get('min', number) <= number <= extra.get('max', number):
                raise SettingsError("{}: {}~{} 사이로 입력하세요".format(label, extra['min'], extra['max']))
            return str(number)
        value = str(value).strip()
        if kind == 'select' and value not in [v for v, _ in self._choices(extra)]:
            raise SettingsError("{}: 알 수 없는 값".format(label))
        if '\n' in value or '\r' in value:
            raise SettingsError("{}: 한 줄로 입력하세요".format(label))
        return value

    def update(self, values):
        """Validate and save the given {"SECTION.option": value}. Return the
        labels of the changed options needing a restart.
        """
        fields = {section + '.' + option: (section, option, label, kind, extra, live)
                  for _, section, option, label, kind, extra, live in self._fields()}
        changes = []
        for key, value in values.items():
            if key not in fields:
                raise SettingsError("알 수 없는 설정: {}".format(key))
            section, option, label, kind, extra, live = fields[key]
            text = self._serialize(kind, value, extra, label)
            if text != str(self.cfg.get(section, option)):
                changes.append((section, option, text, label, live))
        with self._lock:
            for section, option, text, _, _ in changes:
                self.cfg.set(section, option, text)
            if changes:
                self.cfg.save()
        if changes and self.on_change:
            self.on_change([(section, option) for section, option, _, _, _ in changes])
        return {'changed': [label for _, _, _, label, _ in changes],
                'restart': [label for _, _, _, label, live in changes if not live]}


# --- iPad remote ------------------------------------------------------------------
# The remote page asks for actions; they are executed by the main thread (state
# hooks below) as the same key events as the booth keyboard: 'p' to take a
# picture, left/right to choose the number of captures or the frame, return to
# validate the frame. 'reset' clears the last picture and its QR code from the
# wait screen.
STATE_LABELS = {
    'wait': '대기', 'choose': '컷 수 선택', 'chosen': '준비', 'preview': '촬영 중', 'capture': '촬영 중',
    'layout': '프레임 선택', 'processing': '사진 만드는 중', 'print': '완료', 'finish': '완료',
    'failsafe': '오류', 'starting': '시작 중',
}


class RemoteError(ValueError):
    pass


class Remote(object):

    """State of the booth for the remote page, and its pending action."""

    def __init__(self):
        self.app = None
        self._lock = threading.Lock()
        self._pending = None       # (action, value) to execute in the main thread
        self.wanted_captures = None
        self._thumbs = {}

    def state(self):
        app = self.app
        if app is None:
            return {'state': 'starting', 'label': STATE_LABELS['starting']}
        name = getattr(app._machine, 'active_state', None) or 'starting'  # pylint: disable=protected-access
        data = {'state': name, 'label': STATE_LABELS.get(name, name),
                'captures': [int(n) for n in app.capture_choices],
                'capture_nbr': app.capture_nbr,
                'busy': self._pending is not None}
        if name == 'layout':
            previews = getattr(app, 'layout_previews', None) or []
            data.update({'layouts': list(app.layout_choices), 'layout_nbr': app.layout_nbr,
                         'previews': len(previews), 'previews_id': id(previews) if previews else 0})
        if name == 'wait' and getattr(app, 'previous_picture', None) is not None:
            data['picture'] = True              # Shown on the wait screen (can be reset)
            if getattr(app, 'previous_qr_url', None):
                data['qr'] = app.previous_qr_url
        return data

    def request(self, action, value=None):
        """Queue an action asked by the page (one at a time)."""
        state = self.state()['state']
        allowed = {'start': ('wait',), 'reset': ('wait',), 'choose': ('choose',), 'layout': ('layout',)}
        if action not in allowed:
            raise RemoteError("알 수 없는 동작")
        if state not in allowed[action]:
            raise RemoteError("지금은 할 수 없어요 ({})".format(STATE_LABELS.get(state, state)))
        if action in ('start', 'choose') and value is not None:
            if int(value) not in self.app.capture_choices:
                raise RemoteError("선택할 수 없는 컷 수")
            value = int(value)
        if action == 'layout' and value not in ('prev', 'next', 'validate'):
            if not isinstance(value, int) or not 0 <= value < len(self.app.layout_choices):
                raise RemoteError("선택할 수 없는 프레임")
        with self._lock:
            if self._pending is not None:
                raise RemoteError("이전 요청을 처리하는 중이에요")
            self._pending = (action, value)

    def take(self, state):
        """Return the pending action for the given state (main thread)."""
        with self._lock:
            if self._pending and self._pending[0] in {'wait': ('start', 'reset'), 'choose': ('choose',),
                                                      'layout': ('layout',)}.get(state, ()):
                action, self._pending = self._pending, None
                return action
            return None

    def drop_stale(self):
        """Forget a pending action the booth can not execute anymore."""
        with self._lock:
            self._pending = None

    def qr_png(self):
        """Return the PNG of the QR code of the last picture, or None."""
        url = self.state().get('qr')
        if not url:
            return None
        if getattr(self, '_qr', (None, None))[0] != url:
            import qrcode  # pylint: disable=import-outside-toplevel
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            buf = io.BytesIO()
            qr.make_image(fill_color='#0B1230', back_color='white').save(buf, 'PNG')
            self._qr = (url, buf.getvalue())
        return self._qr[1]

    def layout_preview(self, index):
        """Return a JPEG thumbnail of a frame preview, or None."""
        previews = getattr(self.app, 'layout_previews', None) or []
        if not 0 <= index < len(previews):
            return None
        key = (id(previews), index)
        if key not in self._thumbs:
            image = previews[index].copy().convert('RGB')
            image.thumbnail((600, 900), Image.LANCZOS)
            buf = io.BytesIO()
            image.save(buf, 'JPEG', quality=85)
            self._thumbs = {k: v for k, v in self._thumbs.items() if k[0] == id(previews)}
            self._thumbs[key] = buf.getvalue()
        return self._thumbs[key]


def key_event(key):
    """Post a key press in the pygame queue, as the booth keyboard would."""
    import pygame  # pylint: disable=import-outside-toplevel
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode='', scancode=0))


class FactoryHandler(SimpleHTTPRequestHandler):

    """Static files of the page + the pictures API."""

    folder = None
    settings = None
    remote = None
    pin = ''

    def log_message(self, *args):  # pylint: disable=arguments-differ
        pass  # Keep the pibooth console clean (polling every 2 seconds)

    def _send(self, code, body, content_type):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        if url.path == '/api/photos':
            try:
                after = int(parse_qs(url.query).get('after', ['-1'])[0])
            except ValueError:
                after = -1
            latest, entries = self.folder.after(after)
            body = {'latest': latest,
                    'photos': [{'name': name, 'url': 'photos/' + name, 'time': time} for time, name in entries]}
            return self._send(200, json.dumps(body).encode('utf-8'), 'application/json')
        if url.path.startswith('/photos/'):
            path = self.folder.file(url.path[len('/photos/'):])
            if not path:
                return self._send(404, b'Not found', 'text/plain')
            with open(path, 'rb') as fp:
                return self._send(200, fp.read(), 'image/jpeg')
        if url.path == '/api/settings':
            if not self.settings:
                return self._send(404, b'Not found', 'text/plain')
            body = {'groups': self.settings.describe() if self._pin_ok() else [], 'pin': bool(self.pin),
                    'authorized': self._pin_ok()}
            return self._send(200, json.dumps(body, ensure_ascii=False).encode('utf-8'), 'application/json')
        if url.path == '/api/remote' and self.remote:
            return self._json(200, self.remote.state())
        if url.path == '/api/remote/qr.png' and self.remote:
            data = self.remote.qr_png()
            if data is None:
                return self._send(404, b'Not found', 'text/plain')
            return self._send(200, data, 'image/png')
        if url.path.startswith('/api/remote/layout/') and self.remote:
            try:
                data = self.remote.layout_preview(int(url.path.rsplit('/', 1)[1].split('.')[0]))
            except ValueError:
                data = None
            if data is None:
                return self._send(404, b'Not found', 'text/plain')
            return self._send(200, data, 'image/jpeg')
        if url.path == '/settings':
            self.path = '/settings.html'
        elif url.path == '/remote':
            self.path = '/remote.html'
        return super().do_GET()

    def _json(self, code, data):
        return self._send(code, json.dumps(data, ensure_ascii=False).encode('utf-8'), 'application/json')

    def _pin_ok(self):
        return not self.pin or self.headers.get('X-Settings-Pin', '') == self.pin

    def do_POST(self):  # noqa: N802
        if urlparse(self.path).path == '/api/remote' and self.remote:
            try:
                length = int(self.headers.get('Content-Length', '0'))
                body = json.loads(self.rfile.read(min(length, 4096)) or b'{}')
                self.remote.request(body.get('action'), body.get('value'))
            except (RemoteError, ValueError, TypeError) as ex:
                return self._json(409, {'error': str(ex)})
            return self._json(200, {'ok': True})
        if urlparse(self.path).path != '/api/settings' or not self.settings:
            return self._send(404, b'Not found', 'text/plain')
        if not self._pin_ok():
            return self._send(403, json.dumps({'error': 'PIN이 맞지 않습니다'}, ensure_ascii=False).encode('utf-8'),
                              'application/json')
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length > 65536:
                raise SettingsError("요청이 너무 큽니다")
            values = json.loads(self.rfile.read(length) or b'{}').get('values', {})
            result = self.settings.update(values)
        except (SettingsError, ValueError) as ex:
            return self._send(400, json.dumps({'error': str(ex)}, ensure_ascii=False).encode('utf-8'),
                              'application/json')
        return self._send(200, json.dumps(dict(result, ok=True), ensure_ascii=False).encode('utf-8'),
                          'application/json')


def start_server(folder, host, port, directory=PAGE_DIR, settings=None, pin='', remote=None):
    """Start the HTTP server in a daemon thread and return it."""
    handler = type('Handler', (FactoryHandler,), {'folder': folder, 'settings': settings, 'pin': pin,
                                                  'remote': remote})
    server = ThreadingHTTPServer((host, port), partial(handler, directory=directory))
    threading.Thread(target=server.serve_forever, name='factory-http', daemon=True).start()
    return server


def lan_address():
    """Return the IP address of this computer on the local network, or None."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('192.0.2.1', 9))   # No packet is sent: only picks the outgoing interface
        address = sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()
    return None if address.startswith('127.') or address == '0.0.0.0' else address


def server_base(host, port):
    """Return the base URL of the pages and whether the other devices of the
    network can open it."""
    if host in ('', '0.0.0.0'):
        address = lan_address()
        return 'http://{}:{}'.format(address or 'localhost', port), bool(address)
    if host == 'localhost' or host.startswith('127.'):
        return 'http://localhost:{}'.format(port), False
    return 'http://{}:{}'.format(host, port), True


class AddressPanel(object):

    """Addresses of the pages, drawn on the wait screen of the booth: shown
    after the start for ``SHOW_SECONDS``, then toggled with the ``I`` key."""

    SHOW_SECONDS = 30
    NAVY = (14, 26, 58)
    TEXT = (234, 240, 255)
    MUTED = (139, 153, 192)
    ACCENT = (177, 140, 255)

    def __init__(self, base, network):
        self.base = base
        self.network = network
        self.shown_until = time.time() + self.SHOW_SECONDS
        self.pinned = False
        self._cache = (None, None)

    def lines(self):
        return [('사진 공장', self.base + '/'), ('설정', self.base + '/settings'),
                ('리모컨', self.base + '/remote')]

    def is_visible(self):
        return self.pinned or time.time() < self.shown_until

    def toggle(self):
        """Show or hide the panel, return True if it is now hidden."""
        hide = self.is_visible()
        self.pinned = not hide
        self.shown_until = 0
        return hide

    def _font(self, size, role='body'):
        import pygame  # pylint: disable=import-outside-toplevel
        from pibooth import fonts, theme  # pylint: disable=import-outside-toplevel
        try:
            return pygame.font.Font(fonts.get_filename(theme.CURRENT.font(role, 'NotoSansKR-Bold')), size)
        except (ValueError, OSError):
            return pygame.font.Font(fonts.get_filename('NotoSansKR-Bold'), size)

    def render(self, width):
        """Return the panel surface for a window of the given width."""
        if self._cache[0] == width:
            return self._cache[1]
        import pygame  # pylint: disable=import-outside-toplevel
        unit = max(10, width // 80)
        title, label, url, hint = (self._font(int(unit * 1.5), 'heading'), self._font(unit),
                                   self._font(int(unit * 1.1)), self._font(int(unit * 0.85)))
        rows = [(title.render('MacBooth 주소', True, self.ACCENT), 0.6 * unit)]
        for name, link in self.lines():
            rows.append((label.render(name, True, self.MUTED), 0.15 * unit))
            rows.append((url.render(link, True, self.TEXT), 0.5 * unit))
        notes = ['I 키: 주소 보이기/숨기기'] if self.network else \
            ['이 맥에서만 열려요. 아이패드에서 쓰려면', '설정 > 연결 > 접속 허용을 바꾸고 재시작', 'I 키: 주소 보이기/숨기기']
        rows += [(hint.render(note, True, self.MUTED), 0.15 * unit) for note in notes]

        qr = None
        if self.network:
            import qrcode  # pylint: disable=import-outside-toplevel
            code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2)
            code.add_data(self.base + '/remote')
            code.make(fit=True)
            image = code.make_image(fill_color='#0B1230', back_color='white').convert('RGB')
            side = unit * 9
            qr = pygame.transform.scale(pygame.image.fromstring(image.tobytes(), image.size, 'RGB'), (side, side))

        pad = int(unit * 1.2)
        text_w = max(row.get_width() for row, _ in rows)
        text_h = int(sum(row.get_height() + gap for row, gap in rows))
        qr_w = qr.get_width() + pad if qr else 0
        size = (text_w + qr_w + 2 * pad, max(text_h, qr.get_height() if qr else 0) + 2 * pad)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surface, self.NAVY + (235,), surface.get_rect(), border_radius=unit)
        y = pad
        for row, gap in rows:
            surface.blit(row, (pad, y))
            y += row.get_height() + gap
        if qr:
            surface.blit(qr, (pad + text_w + pad, pad))
        self._cache = (width, surface)
        return surface

    def draw(self, win):
        """Draw the panel in the top right corner of the window."""
        rect = win.surface.get_rect()
        surface = self.render(rect.width)
        margin = max(10, rect.width // 80)
        return win.surface.blit(surface, (rect.right - surface.get_width() - margin, margin))


_FOLDER = None
_SERVER = None
_PENDING = threading.Event()   # Live settings saved by the page, to apply on the wait screen


def _settings_changed(changes):
    """Called from the server thread: the factory folder limit is applied now,
    the booth options at the next wait screen (main thread)."""
    if _FOLDER and (SECTION, 'keep') in changes:
        _FOLDER.keep = _SETTINGS.cfg.getint(SECTION, 'keep')
        _FOLDER.prune()
    _PENDING.set()


_SETTINGS = None
_REMOTE = Remote()
_PANEL = None


@pibooth.hookimpl
def pibooth_configure(cfg):
    """Declare the factory page options."""
    cfg.add_option(SECTION, 'enabled', True,
                   "Serve the photo factory display page", "Factory page", ['True', 'False'])
    cfg.add_option(SECTION, 'host', '127.0.0.1',
                   "Address to listen on ('0.0.0.0' to open the page from another computer)")
    cfg.add_option(SECTION, 'port', 8770,
                   "Port of the photo factory page")
    cfg.add_option(SECTION, 'photos_dir', '',
                   "Folder of the pictures shown by the page (empty: 'factory' in the pictures directory)")
    cfg.add_option(SECTION, 'keep', 50,
                   "Number of pictures kept in the folder (the oldest ones are deleted)")
    cfg.add_option(SECTION, 'directory', '',
                   "Folder of the factory page (empty: the 'factory' folder of this repository)")
    cfg.add_option(SECTION, 'settings_pin', '',
                   "PIN asked by the settings page (/settings), recommended with host = 0.0.0.0")


@pibooth.hookimpl
def pibooth_startup(cfg, app):
    """Prepare the pictures folder and start the page server."""
    global _FOLDER, _SERVER, _SETTINGS, _PANEL
    _REMOTE.app = app
    if not cfg.getboolean(SECTION, 'enabled'):
        return
    photos_dir = cfg.getpath(SECTION, 'photos_dir') or \
        osp.join(cfg.gettuple('GENERAL', 'directory', 'path')[0], 'factory')
    _FOLDER = PhotoFolder(photos_dir, cfg.getint(SECTION, 'keep'))
    _FOLDER.prune()
    directory = cfg.getpath(SECTION, 'directory') or PAGE_DIR
    host, port = cfg.get(SECTION, 'host'), cfg.getint(SECTION, 'port')
    try:
        _SETTINGS = Settings(cfg, _settings_changed)
        _SERVER = start_server(_FOLDER, host, port, directory, _SETTINGS, str(cfg.get(SECTION, 'settings_pin')),
                               _REMOTE)
        base, network = server_base(host, port)
        _PANEL = AddressPanel(base, network)
        LOGGER.info("Photo factory page: %s/ (pictures in '%s', settings on /settings, remote on /remote)",
                    base, photos_dir)
    except OSError as ex:
        LOGGER.error("Photo factory page not started on port %s: %s", port, ex)


@pibooth.hookimpl
def state_processing_exit(app):
    """Publish the new final picture to the page."""
    path = getattr(app, 'previous_picture_file', None)
    if _FOLDER and path and osp.isfile(path):
        try:
            _FOLDER.add(path)
        except Exception as ex:  # pylint: disable=broad-except
            LOGGER.error("Picture not published to the factory page: %s", ex)


@pibooth.hookimpl
def state_wait_enter():
    """Show the address of the pages in the window title."""
    if _PANEL:
        import pygame  # pylint: disable=import-outside-toplevel
        pygame.display.set_caption('MacBooth  ·  {}'.format(_PANEL.base))


@pibooth.hookimpl
def state_wait_do(app, win, events):
    """Ask pibooth to apply the settings saved by the page (main loop, between
    two sessions), start a session asked by the remote and draw the addresses
    of the pages (key I)."""
    if _PANEL:
        import pygame  # pylint: disable=import-outside-toplevel
        if any(event.type == pygame.KEYDOWN and event.key == pygame.K_i for event in events):
            if _PANEL.toggle():
                win.show_intro(app.previous_picture, app.printer.is_ready() and app.count.remaining_duplicates > 0)
        elif _PANEL.shown_until and not _PANEL.is_visible():
            _PANEL.shown_until = 0   # End of the display after the start
            win.show_intro(app.previous_picture, app.printer.is_ready() and app.count.remaining_duplicates > 0)
        if _PANEL.is_visible():
            _PANEL.draw(win)
    if _PENDING.is_set():
        _PENDING.clear()
        app.settings_changed = True
    action = _REMOTE.take('wait')
    if action and action[0] == 'reset':
        reset_wait_screen(app, win)
    elif action:
        import pygame  # pylint: disable=import-outside-toplevel
        _REMOTE.wanted_captures = action[1]    # Number of captures chosen on the remote
        key_event(pygame.K_p)


def reset_wait_screen(app, win):
    """Forget the last picture: the wait screen (booth and remote) only
    invites to take a picture, without the picture and its QR code."""
    app.previous_picture = None
    app.previous_animated = None
    app.previous_qr_base = None
    app.previous_qr_url = None
    win.show_intro(None, app.printer.is_ready() and app.count.remaining_duplicates > 0)


@pibooth.hookimpl
def state_choose_do(app):
    """Choose the number of captures asked by the remote (left/right keys)."""
    import pygame  # pylint: disable=import-outside-toplevel
    action = _REMOTE.take('choose')
    wanted = action[1] if action else _REMOTE.wanted_captures
    _REMOTE.wanted_captures = None
    if wanted in app.capture_choices:
        key_event(pygame.K_LEFT if wanted == app.capture_choices[0] else pygame.K_RIGHT)


@pibooth.hookimpl
def state_layout_do(app):
    """Move in the frames or validate one, as asked by the remote."""
    import pygame  # pylint: disable=import-outside-toplevel
    action = _REMOTE.take('layout')
    if not action:
        return
    value = action[1]
    if isinstance(value, int):
        app.layout_nbr = value
    else:
        key_event({'prev': pygame.K_LEFT, 'next': pygame.K_RIGHT, 'validate': pygame.K_RETURN}[value])


@pibooth.hookimpl
def state_choose_exit():
    _REMOTE.drop_stale()


@pibooth.hookimpl
def state_layout_exit():
    _REMOTE.drop_stale()


@pibooth.hookimpl
def state_preview_enter():
    """The session is started: a remote choice can not leak to the next one."""
    _REMOTE.wanted_captures = None
    _REMOTE.drop_stale()


@pibooth.hookimpl
def pibooth_cleanup():
    if _SERVER:
        _SERVER.shutdown()
