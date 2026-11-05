#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Local admin server for pibooth: a visual picture-template manager.

It serves the *Macbooth Template Studio* editor and connects it to the local
pibooth installation, so templates designed in the browser are:

- saved straight into the pibooth configuration folder,
- previewed with the real pibooth rendering engine (exactly the printed result),
- registered in ``pibooth.cfg`` (``[PICTURE] template`` and ``[GENERAL] plugins``).

Run it with::

    python admin/pibooth_admin.py                 # uses ~/.config/pibooth
    python admin/pibooth_admin.py --config DIR     # custom config folder
    python admin/pibooth_admin.py --port 8890

then open http://localhost:8080 in a browser.
"""

import io
import os
import re
import sys
import json
import argparse
import tempfile
import webbrowser
import os.path as osp
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from configparser import RawConfigParser

HERE = osp.dirname(osp.abspath(__file__))
REPO = osp.dirname(HERE)
EDITOR_HTML = osp.join(REPO, 'tools', 'template_editor.html')
PLUGIN_PATH = osp.join(REPO, 'plugins', 'pibooth_picture_template.py')

# Make the vendored plugin importable for the real-preview rendering
sys.path.insert(0, osp.join(REPO, 'plugins'))

SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 _.-]*$')
SAMPLE_COLORS = ((138, 90, 68), (74, 122, 106), (201, 138, 43), (90, 90, 168))


def default_config_dir():
    """Return the default pibooth configuration folder."""
    return osp.expanduser(osp.join('~', '.config', 'pibooth'))


def slugify(name):
    """Return a safe file name (without extension) for a template name."""
    slug = re.sub(r'[^a-z0-9]+', '-', (name or 'template').lower()).strip('-')
    return slug or 'template'


def list_templates(config_dir):
    """Return the templates found in the configuration folder, newest first.

    :return: list of dicts {name, file, type, captures}
    """
    result = []
    if not osp.isdir(config_dir):
        return result
    for fname in sorted(os.listdir(config_dir)):
        path = osp.join(config_dir, fname)
        lower = fname.lower()
        if lower.endswith('.json'):
            try:
                with open(path, encoding='utf-8') as fp:
                    data = json.load(fp)
                if data.get('format') != 'pibooth-template':
                    continue
                result.append({'name': data.get('name', fname), 'file': fname,
                               'type': 'json', 'captures': data.get('captures')})
            except (ValueError, OSError):
                continue
        elif lower.endswith('.xml') and lower != 'translations.cfg':
            if _looks_like_drawio(path):
                result.append({'name': osp.splitext(fname)[0], 'file': fname,
                               'type': 'xml', 'captures': None})
    result.sort(key=lambda t: osp.getmtime(osp.join(config_dir, t['file'])), reverse=True)
    return result


def _looks_like_drawio(path):
    try:
        with open(path, encoding='utf-8', errors='ignore') as fp:
            return 'mxfile' in fp.read(400) or 'mxGraphModel' in fp.read(400)
    except OSError:
        return False


def load_template(config_dir, fname):
    """Return the JSON content of a template file (only .json)."""
    if not SAFE_NAME.match(fname) or not fname.lower().endswith('.json'):
        raise ValueError("Invalid template file name")
    path = osp.join(config_dir, fname)
    with open(path, encoding='utf-8') as fp:
        return json.load(fp)


def save_template(config_dir, data):
    """Write a template JSON into the configuration folder.

    :return: the file name written
    """
    if data.get('format') != 'pibooth-template':
        raise ValueError("Not a pibooth template")
    if not osp.isdir(config_dir):
        os.makedirs(config_dir)
    fname = slugify(data.get('name')) + '.json'
    with open(osp.join(config_dir, fname), 'w', encoding='utf-8') as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
    return fname


def render_preview(data, size=None):
    """Render a template with placeholder photos through the real pibooth
    engine and return the PNG bytes.
    """
    import pibooth_picture_template as ppt  # noqa: E402  (optional, needs pibooth installed)
    from PIL import Image

    captures = int(data.get('captures', 1))
    images = []
    for i in range(max(1, captures)):
        color = SAMPLE_COLORS[i % len(SAMPLE_COLORS)]
        images.append(_sample_photo(color, i + 1))

    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as fp:
        json.dump(data, fp)
        tmp = fp.name
    try:
        template = ppt.JsonTemplate(tmp)
        orientation = template.orientation
        factory = template.build_factory(orientation, images)
        # Provide the two footer texts referenced by the template
        factory.add_text("Youngchan & Friends", "Amatic-Bold", (38, 34, 28), 'center')
        factory.add_text("2026 . 09 . 16", "Amatic-Bold", (140, 133, 120), 'center')
        picture = factory.build()
    finally:
        os.remove(tmp)

    if size:
        picture = picture.copy()
        picture.thumbnail(size, Image.LANCZOS)
    buf = io.BytesIO()
    picture.save(buf, 'PNG')
    return buf.getvalue()


def _sample_photo(color, number):
    """Return a placeholder capture image (a soft gradient with a number)."""
    from PIL import Image, ImageDraw, ImageFont
    width, height = 1200, 900
    top = color
    bottom = tuple(max(0, c - 45) for c in color)
    base = Image.new('RGB', (width, height))
    px = base.load()
    for y in range(height):
        ratio = y / height
        row = tuple(int(top[c] * (1 - ratio) + bottom[c] * ratio) for c in range(3))
        for x in range(width):
            px[x, y] = row
    draw = ImageDraw.Draw(base)
    try:
        font = ImageFont.truetype(_font_path(), 320)
    except OSError:
        font = ImageFont.load_default()
    text = str(number)
    left, top_, right, bottom_ = draw.textbbox((0, 0), text, font=font)
    draw.text(((width - (right - left)) / 2 - left, (height - (bottom_ - top_)) / 2 - top_),
              text, (255, 255, 255), font=font)
    return base


def _font_path():
    from pibooth import fonts
    return fonts.get_filename('Amatic-Bold')


def register_in_config(config_dir, template_file, plugin_path=PLUGIN_PATH):
    """Add the template to '[PICTURE] template' and the plugin to
    '[GENERAL] plugins' in pibooth.cfg (created if missing). Idempotent.

    :return: dict with the updated option values
    """
    cfg_path = osp.join(config_dir, 'pibooth.cfg')
    parser = RawConfigParser(inline_comment_prefixes=None)
    if osp.isfile(cfg_path):
        parser.read(cfg_path, encoding='utf-8')

    template_path = osp.join(config_dir, template_file)
    templates = _merge_quoted(_get(parser, 'PICTURE', 'template'), template_path)
    plugins = _merge_quoted(_get(parser, 'GENERAL', 'plugins'), plugin_path)

    _set(parser, 'PICTURE', 'template', templates)
    _set(parser, 'GENERAL', 'plugins', plugins)
    with open(cfg_path, 'w', encoding='utf-8') as fp:
        parser.write(fp)
    return {'template': templates, 'plugins': plugins}


def _get(parser, section, option):
    if parser.has_section(section) and parser.has_option(section, option):
        return parser.get(section, option)
    return ''


def _set(parser, section, option, value):
    if not parser.has_section(section):
        parser.add_section(section)
    parser.set(section, option, value)


def _merge_quoted(current, new_path):
    """Return the option value that contains 'new_path', keeping the existing
    quoted paths. The value is a single quoted path or a tuple of them.
    """
    paths = re.findall(r'"([^"]*)"', current or '')
    if not paths and current and current.strip():
        paths = [current.strip()]
    paths = [p for p in paths if p]
    if new_path not in paths:
        paths.append(new_path)
    if len(paths) == 1:
        return '"{}"'.format(paths[0])
    return '(' + ', '.join('"{}"'.format(p) for p in paths) + ')'


class AdminHandler(BaseHTTPRequestHandler):

    config_dir = default_config_dir()

    def log_message(self, *args):
        pass  # Quiet

    def _send(self, code, body, ctype='application/json'):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length) or b'{}')

    def do_GET(self):  # noqa: N802
        if self.path in ('/', '/index.html'):
            try:
                with open(EDITOR_HTML, 'rb') as fp:
                    self._send(200, fp.read(), 'text/html; charset=utf-8')
            except OSError:
                self._send(500, {'error': 'editor html not found'})
        elif self.path == '/api/ping':
            self._send(200, {'ok': True, 'config_dir': self.config_dir})
        elif self.path == '/api/templates':
            self._send(200, {'templates': list_templates(self.config_dir)})
        elif self.path.startswith('/api/template/'):
            try:
                self._send(200, {'template': load_template(self.config_dir, self.path.split('/', 3)[3])})
            except (ValueError, OSError) as ex:
                self._send(404, {'error': str(ex)})
        else:
            self._send(404, {'error': 'not found'})

    def do_POST(self):  # noqa: N802
        try:
            if self.path == '/api/template':
                fname = save_template(self.config_dir, self._read_json())
                self._send(200, {'ok': True, 'file': fname})
            elif self.path == '/api/preview':
                png = render_preview(self._read_json(), size=(900, 900))
                self._send(200, png, 'image/png')
            elif self.path == '/api/register':
                fname = self._read_json().get('file')
                if not fname or not SAFE_NAME.match(fname):
                    raise ValueError("Missing template file")
                self._send(200, {'ok': True, 'config': register_in_config(self.config_dir, fname)})
            else:
                self._send(404, {'error': 'not found'})
        except Exception as ex:  # pylint: disable=broad-except
            self._send(400, {'error': str(ex)})


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--config', default=default_config_dir(),
                        help="pibooth configuration folder (default: %(default)s)")
    parser.add_argument('--port', type=int, default=8080, help="port to serve on (default: %(default)s)")
    parser.add_argument('--no-browser', action='store_true', help="do not open the browser")
    options = parser.parse_args()

    AdminHandler.config_dir = osp.abspath(osp.expanduser(options.config))
    server = ThreadingHTTPServer(('127.0.0.1', options.port), AdminHandler)
    url = 'http://localhost:{}'.format(options.port)
    print("Macbooth Template Studio -> {}".format(url))
    print("Configuration folder    : {}".format(AdminHandler.config_dir))
    if not options.no_browser:
        try:
            webbrowser.open(url)
        except Exception:  # pylint: disable=broad-except
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == '__main__':
    main()
