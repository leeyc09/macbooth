# -*- coding: utf-8 -*-

"""Pibooth plugin to display a QR Code on the screen during idle time.

Vendored copy of pibooth-qrcode with an added ``[QRCODE] size`` option to
control the QR code size in pixels (the PyPI version renders a fixed small
size). Uninstall the ``pibooth-qrcode`` package when using this file so the
hooks are not registered twice.
"""

try:
    import qrcode
except ImportError:
    qrcode = None
    pass  # When running the setup.py, qrcode is not yet installed
import pygame
import pibooth
from pibooth import language, theme
from pibooth.view.background import multiline_text_to_surfaces

__version__ = "1.0.2"


SECTION = 'QRCODE'
# The 'size' and 'offset' options are given for a window of this height (short
# side); they are scaled with the actual window so the QR code keeps the same
# proportions (and stays inside the screen frame) on a bigger screen.
REFERENCE_SIZE = 720
LOCATIONS = ['topleft', 'topright',
             'bottomleft', 'bottomright',
             'midtop-left', 'midtop-right',
             'midbottom-left', 'midbottom-right']


@pibooth.hookimpl
def pibooth_configure(cfg):
    """Declare the new configuration options"""
    cfg.add_option(SECTION, 'prefix_url', "https://github.com/pibooth/pibooth",
                   "URL which may be composed of variables: {picture}, {count}, {url} (shared link) and "
                   "{key} (uploaded object key, see the R2 plugin)")
    cfg.add_option(SECTION, 'foreground', (255, 255, 255),
                   "Foreground color",
                   "Color", (255, 255, 255))
    cfg.add_option(SECTION, 'background', (0, 0, 0),
                   "Background color",
                   "Background color", (0, 0, 0))
    cfg.add_option(SECTION, 'size', 300,
                   "Size of the QR code in pixels for a 720 pixels high window (scaled with the window)",
                   "Size", [str(i) for i in range(100, 601, 50)])
    cfg.add_option(SECTION, 'side_text', "",
                   "Optional text displayed close to the QR code",
                   "Side text", "")
    cfg.add_option(SECTION, 'offset', (20, 40),
                   "Offset (x, y) from location for a 720 pixels high window (scaled with the window)")
    cfg.add_option(SECTION, 'wait_location', "bottomleft",
                   "Location on 'wait' state: {}".format(', '.join(LOCATIONS)),
                   "Location on wait screen", LOCATIONS)
    cfg.add_option(SECTION, 'print_location', "bottomright",
                   "Location on 'print' state: {}".format(', '.join(LOCATIONS)),
                   "Location on print screen", LOCATIONS)


def get_scale(win_rect):
    """Return the ratio between the window and the reference size."""
    return min(win_rect.size) / REFERENCE_SIZE


def get_scaled_qr(cfg, app, win_rect):
    """Return the QR code surface at the size of the 'size' option scaled to
    the window (cached until the size changes), also set in ``app.previous_qr``.
    """
    base = app.previous_qr_base
    size = int(cfg.getint(SECTION, 'size') * get_scale(win_rect)) or base.get_width()
    if app.previous_qr is None or app.previous_qr.get_width() != size:
        # Nearest neighbour keeps the modules sharp, as the QR code is made of squares
        app.previous_qr = pygame.transform.scale(base, (size, size))
    return app.previous_qr


def get_scaled_offset(cfg, win_rect):
    scale = get_scale(win_rect)
    return tuple(int(v * scale) for v in cfg.gettuple(SECTION, 'offset', int, 2))


def get_qrcode_rect(win_rect, qrcode_image, location, offset):
    sublocation = ''
    if '-' in location:
        location, sublocation = location.split('-')
    pos = list(getattr(win_rect, location))
    if 'top' in location:
        pos[1] += offset[1]
    else:
        pos[1] -= offset[1]
    if 'left' in location:
        pos[0] += offset[0]
    else:
        pos[0] -= offset[0]
    if 'mid' in location:
        if 'left' in sublocation:
            pos[0] -= qrcode_image.get_size()[0] // 2
        else:
            pos[0] += (qrcode_image.get_size()[0] // 2 + 2 * offset[0])
    qr_rect = qrcode_image.get_rect(**{location: pos})
    return qr_rect


def get_text_rect(win_rect, qrcode_rect, location, margin=None):
    if margin is None:
        margin = int(10 * get_scale(win_rect))
    text_rect = pygame.Rect(0, 0, win_rect.width // 6, qrcode_rect.height)
    sublocation = ''
    if '-' in location:
        location, sublocation = location.split('-')
    text_rect.top = qrcode_rect.top
    if 'left' in location:
        text_rect.left = qrcode_rect.right + margin
    else:
        text_rect.right = qrcode_rect.left - margin
    if 'mid' in location:
        if 'left' in sublocation:
            text_rect.right = qrcode_rect.left - margin
        else:
            text_rect.left = qrcode_rect.right + margin
    return text_rect


def get_side_text(cfg):
    """Return the text displayed close to the QR code: the theme one (in the
    current language), else the ``side_text`` option.
    """
    return theme.CURRENT.text('qrcode', language.CURRENT, cfg.get(SECTION, 'side_text'))


def get_colors(cfg):
    """Return the (foreground, background) RGB colors of the QR code: the
    theme ones, else the options.
    """
    return (theme.CURRENT.role_color('qrcode', 'foreground', cfg.gettyped(SECTION, 'foreground')),
            theme.CURRENT.role_color('qrcode', 'background', cfg.gettyped(SECTION, 'background')))


def get_text_color(cfg):
    """Return the color of the side text (the booth text color)."""
    return theme.CURRENT.role_color('booth', 'text', cfg.gettyped('WINDOW', 'text_color'))


@pibooth.hookimpl
def pibooth_startup(cfg):
    """
    Check the coherence of options.
    """
    for state in ('wait', 'print'):
        if cfg.get(SECTION, '{}_location'.format(state)) not in LOCATIONS:
            raise ValueError("Unknown QR code location on '{}' state '{}'".format(
                             state, cfg.get(SECTION, '{}_location'.format(state))))


def layout_wait(cfg, app, win):
    """Compute the QR code and side text surfaces/positions of the wait view
    for the current window size.
    """
    win_rect = win.get_rect()
    location = cfg.get(SECTION, 'wait_location')
    qr_image = get_scaled_qr(cfg, app, win_rect)
    app.qr_rect = get_qrcode_rect(win_rect, qr_image, location, get_scaled_offset(cfg, win_rect))
    app.qr_texts = []
    side_text = get_side_text(cfg)
    if side_text:
        text_rect = get_text_rect(win_rect, app.qr_rect, location)
        app.qr_texts = multiline_text_to_surfaces(side_text, get_text_color(cfg), text_rect, 'bottom-left')
    app.qr_window_size = win_rect.size


def draw_wait(app, win):
    win.surface.blit(app.previous_qr, app.qr_rect.topleft)
    for text, rect in app.qr_texts:
        win.surface.blit(text, rect)


@pibooth.hookimpl
def state_wait_enter(cfg, app, win):
    """
    Display the QR Code on the wait view.
    """
    if getattr(app, 'previous_qr_base', None) and app.previous_picture:
        layout_wait(cfg, app, win)
        draw_wait(app, win)


@pibooth.hookimpl
def state_wait_do(cfg, app, win):
    """
    Redraw the QR Code because it may have been erased by a screen update (
    for instance, if a print is done), at the new size if the window has been
    resized (e.g. switched to full screen) meanwhile.
    """
    if getattr(app, 'previous_qr_base', None) and hasattr(app, 'qr_rect') and app.previous_picture:
        if win.get_rect().size != getattr(app, 'qr_window_size', None):
            layout_wait(cfg, app, win)
        draw_wait(app, win)


@pibooth.hookimpl(trylast=True)
def state_processing_exit(cfg, app):
    """
    Generate the QR Code and store it in the application.
    """
    if qrcode is None:
        raise ModuleNotFoundError("No module named 'qrcode'")
    qr = qrcode.QRCode(version=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_L,
                       box_size=3,
                       border=2)  # Quiet zone: easier to scan on a dark screen

    url_vars = {'picture': app.picture_filename,
                'count': app.count,
                'url': getattr(app, 'previous_picture_url', None) or '',
                'key': getattr(app, 'previous_picture_key', None) or ''}

    # Also kept for the other plugins (e.g. the iPad remote shows the same QR code)
    app.previous_qr_url = cfg.get(SECTION, 'prefix_url').format(**url_vars)
    qr.add_data(app.previous_qr_url)
    qr.make(fit=True)
    foreground, background = get_colors(cfg)
    qrcode_fill_color = '#%02x%02x%02x' % foreground
    qrcode_background_color = '#%02x%02x%02x' % background

    image = qr.make_image(fill_color=qrcode_fill_color, back_color=qrcode_background_color)
    # Scaled to the window when displayed (see get_scaled_qr)
    app.previous_qr_base = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
    app.previous_qr = None


@pibooth.hookimpl
def state_print_enter(cfg, app, win):
    """
    Display the QR Code on the print view.
    """
    win_rect = win.get_rect()
    location = cfg.get(SECTION, 'print_location')
    qr_image = get_scaled_qr(cfg, app, win_rect)
    qrcode_rect = get_qrcode_rect(win_rect, qr_image, location, get_scaled_offset(cfg, win_rect))
    side_text = get_side_text(cfg)
    if side_text:
        text_rect = get_text_rect(win_rect, qrcode_rect, location)
        texts = multiline_text_to_surfaces(side_text, get_text_color(cfg), text_rect, 'bottom-left')
        for text, rect in texts:
            win.surface.blit(text, rect)

    win.surface.blit(qr_image, qrcode_rect.topleft)
