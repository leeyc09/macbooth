# -*- coding: utf-8 -*-

"""Build the generated files of a pibooth theme from its ``theme.json``.

Usage::

    python tools/build_theme.py <theme name or folder> [--worker share-worker/src/theme.js]

It writes into the theme folder (only for themes with a ``build`` section):

- ``templates/<name>-4.json`` and ``templates/<name>-1.json``: the print
  templates (pibooth JSON format, background embedded as a JPEG data URI),
- ``assets/booth-background.jpg``: the background of the booth screens,
- ``assets/booth-capture-group.png`` and ``assets/booth-processing.png``: the
  illustrations of the capture and processing screens (``pictograms``).

With ``--worker``, it also writes the theme of the share web page (colors,
fonts, texts, logo) as a JavaScript module for ``share-worker``.

Every color, font, image and text comes from the theme tokens, so another
theme with the same structure gets its own look without code change. The
``galaxy`` style draws: a base color with blurred glow orbs and a starfield,
photos in gradient frames with a glow, then logo, mascot, tagline and event
info in the footer. On the 1 capture template the mascot overlaps the
bottom-right corner of the photo (``build.mascot_overlap``).
"""

import os
import sys
import json
import base64
import random
import argparse
import os.path as osp
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, osp.dirname(osp.dirname(osp.abspath(__file__))))
from pibooth import theme as themes  # noqa: E402

WIDTH, HEIGHT = 2400, 3600   # JsonTemplate.PORTRAIT_SIZE
BOOTH_SIZE = (1920, 1080)
MARGIN = 120
RADIUS = 0.06                # rounded mask of the captures (ratio of the short side)


def to_data_uri(image, fmt="JPEG"):
    buf = BytesIO()
    if fmt == "PNG":
        image.save(buf, "PNG", optimize=True)
    else:
        image.convert("RGB").save(buf, "JPEG", quality=90, optimize=True, progressive=True)
    return "data:image/{};base64,".format(fmt.lower()) + base64.b64encode(buf.getvalue()).decode("ascii")


def gradient(size, start, end, horizontal=False):
    """Return an RGB linear gradient (diagonal 135deg by default)."""
    n = 64
    ramp = Image.new("L", (n, n))
    ramp.putdata([int(255 * (x if horizontal else (x + y) / 2) / (n - 1))
                  for y in range(n) for x in range(n)])
    ramp = ramp.resize(size, Image.BILINEAR)
    return Image.composite(Image.new("RGB", size, end), Image.new("RGB", size, start), ramp)


def sparkle(draw, cx, cy, size, color):
    """4-point star glyph as a polygon."""
    s, k = size, size * 0.22
    draw.polygon([(cx, cy - s), (cx + k, cy - k), (cx + s, cy), (cx + k, cy + k),
                  (cx, cy + s), (cx - k, cy + k), (cx - s, cy), (cx - k, cy - k)], fill=color)


def tracked_text(draw, xy, text, fnt, fill, tracking, anchor="ls"):
    """Draw text with letter spacing. Return its width."""
    x, y = xy
    widths = [fnt.getlength(ch) + tracking for ch in text]
    total = sum(widths) - tracking
    if anchor[0] == "r":
        x -= total
    elif anchor[0] == "m":
        x -= total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill, anchor="l" + anchor[1])
        x += w
    return total


class GalaxyBuilder(object):

    """Draw the generated images of a theme with the ``galaxy`` style."""

    def __init__(self, theme):
        self.theme = theme
        self.build = theme.section("build")
        color = theme.color
        self.base = color("background")
        self.surface = color("surface", self.base)
        self.accent = color("accent")
        self.accent_2 = color("accent-2", self.accent)
        self.accent_3 = color("accent-3", self.accent_2)
        self.text = color("text")
        self.text_dim = color("text-dim", self.text)
        self.text_muted = color("text-muted", self.text_dim)
        self.line = color("line", self.text_muted)
        self.grad_text = [color(c) for c in theme.section("gradients").get("text", ["accent", "accent-3"])]

    def font(self, token, size):
        return ImageFont.truetype(self.theme.font(token), size)

    def asset(self, name):
        """Return an asset of the theme cropped to its visible content."""
        image = Image.open(self.theme.asset(name)).convert("RGBA")
        return image.crop(image.getbbox())

    # Background ---------------------------------------------------------

    def base_canvas(self, size, seed=2026):
        """Base color, blurred glow orbs (accent ramp) and a starfield."""
        width, height = size
        scale = width / WIDTH
        canvas = Image.new("RGBA", size, self.base + (255,))
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for fx, fy, fr, color, alpha in ((0.12, 0.14, 0.29, self.accent, 120), (0.92, 0.42, 0.33, self.accent_2, 110),
                                         (0.2, 0.8, 0.31, self.accent_2, 90), (0.83, 0.86, 0.25, self.accent, 90)):
            cx, cy, r = fx * width, fy * height, fr * WIDTH * scale
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color + (alpha,))
        canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(260 * scale)))

        rnd = random.Random(seed)
        draw = ImageDraw.Draw(canvas, "RGBA")
        colors = [self.text, self.accent_3, self.accent, (255, 255, 255)]
        for _ in range(int(900 * width * height / (WIDTH * HEIGHT))):
            x, y = rnd.randrange(width), rnd.randrange(height)
            r = max(1, int(rnd.choice([1, 1, 2, 2, 3, 4]) * max(scale, 0.6)))
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rnd.choice(colors) + (rnd.randint(70, 220),))
        return canvas

    def booth_background(self):
        return self.base_canvas(BOOTH_SIZE, seed=11).convert("RGB")

    # Booth screen illustrations (full color, transparent) -----------------

    def _fit(self, name, height):
        image = self.asset(name)
        return image.resize((int(image.width * height / image.height), height), Image.LANCZOS)

    def booth_capture_group(self):
        """Mascots posing together, left of the capture screen."""
        canvas = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        poses = self.build.get("capture_group", ["mascot_wave", "mascot_cheer", "mascot_welcome"])
        heights = [440, 560, 420]
        x = 0
        for name, height in zip(poses, heights):
            image = self._fit(name, height)
            canvas.alpha_composite(image, (x, 600 - height))
            x += int(image.width * .78)
        return canvas.crop(canvas.getbbox())

    def booth_processing(self):
        """Photos hanging on a line in the brand frames, a mascot working
        under them (the text of the screen is drawn below, last 20%).
        """
        width, height = 1440, 900
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        # The line, slightly curved
        points = [(x, 150 + int(40 * (1 - ((x - width / 2) / (width / 2)) ** 2))) for x in range(80, width - 79, 20)]
        draw.line(points, fill=self.text_muted + (255,), width=5, joint="curve")
        frame_w, frame_h = 230, 280
        for i, cx in enumerate((width / 2 - 300, width / 2, width / 2 + 300)):
            top = 150 + int(40 * (1 - ((cx - width / 2) / (width / 2)) ** 2)) + 6
            box = (int(cx - frame_w / 2), top, int(cx + frame_w / 2), top + frame_h)
            frame = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            self.photo_frame(frame, box, 18)
            # Photo still developing: a gradient well with a sparkle
            inner = (box[0] + 16, box[1] + 16, box[2] - 16, box[3] - 56)
            mask = Image.new("L", canvas.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(inner, 10, fill=255)
            frame.paste(gradient((inner[2] - inner[0], inner[3] - inner[1]), self.surface, self.accent_2),
                        inner[:2], mask.crop(inner))
            sparkle(ImageDraw.Draw(frame), (inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2, 28, self.accent_3)
            angle = (-5, 2, 6)[i]
            canvas.alpha_composite(frame.rotate(angle, center=(cx, top), resample=Image.BICUBIC))
            # Clip on the line
            draw.rounded_rectangle((cx - 14, top - 22, cx + 14, top + 18), 6, fill=self.accent_3 + (255,))
        mascot = self._fit(self.build.get("processing_mascot", "mascot_laptop"), 250)
        canvas.alpha_composite(mascot, (width // 2 - mascot.width // 2, 470))
        return canvas

    # Print templates ----------------------------------------------------

    def photo_frame(self, canvas, box, radius_px):
        """Glow + gradient border + surface well where a capture goes."""
        x0, y0, x1, y1 = box
        border = 10
        for offset, blur, color, alpha in ((40, 70, self.accent, 110), (80, 150, self.accent_2, 120)):
            layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).rounded_rectangle((x0, y0 + offset, x1, y1 + offset), radius_px, fill=color + (alpha,))
            canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
        outer = (x0 - border, y0 - border, x1 + border, y1 + border)
        size = (outer[2] - outer[0], outer[3] - outer[1])
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius_px + border, fill=255)
        canvas.paste(gradient(size, self.grad_text[0], self.grad_text[-1]), outer[:2], mask)
        ImageDraw.Draw(canvas).rounded_rectangle(box, radius_px, fill=self.surface)

    def gradient_text(self, canvas, xy, text, fnt, tracking=0, anchor="ms"):
        mask = Image.new("L", canvas.size, 0)
        tracked_text(ImageDraw.Draw(mask), xy, text, fnt, 255, tracking, anchor=anchor)
        box = mask.getbbox()
        if not box:
            return
        fill = Image.new("RGB", canvas.size, self.grad_text[0])
        fill.paste(gradient((box[2] - box[0], box[3] - box[1]), self.grad_text[0], self.grad_text[-1], horizontal=True),
                   box[:2])
        canvas.paste(fill, (0, 0), mask)

    def header(self, canvas, top):
        draw = ImageDraw.Draw(canvas)
        eyebrow = self.font("display", 54)
        if self.theme.event("eyebrow"):
            sparkle(draw, MARGIN + 26, top - 20, 26, self.accent_3)
            tracked_text(draw, (MARGIN + 76, top), self.theme.event("eyebrow"), eyebrow, self.accent_3, 0.22 * 54)
        if self.theme.event("label"):
            tracked_text(draw, (WIDTH - MARGIN, top), self.theme.event("label"), eyebrow, self.text_dim, 0.22 * 54,
                         anchor="rs")

    def mascot_overlay(self, mascot):
        """Mascot with a soft glow baked around it, to stand out over a photo."""
        pad = 90
        size = (mascot.width + 2 * pad, mascot.height + 2 * pad)
        alpha = Image.new("L", size, 0)
        alpha.paste(mascot.getchannel("A"), (pad, pad + 30))
        shadow = Image.new("RGBA", size, self.accent_2 + (0,))
        shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(40)).point(lambda a: int(a * 0.75)))
        shadow.alpha_composite(mascot, (pad, pad))
        return shadow, pad

    def footer(self, canvas, top, overlap_box=None):
        """Logo + mascot + tagline + event info. With ``overlap_box`` the
        mascot is put over that photo corner and returned as an image slot.
        """
        draw = ImageDraw.Draw(canvas)
        bottom_line = HEIGHT - 250
        room = bottom_line - top - 260

        lockup = self.asset("logo")
        lw = min(1180, int(room * lockup.width / lockup.height))
        lockup = lockup.resize((lw, int(lw * lockup.height / lockup.width)), Image.LANCZOS)

        mascot = self.asset("mascot")
        mh = int(min(room, 900) * (0.9 if overlap_box else 1))
        mascot = mascot.resize((int(mh * mascot.width / mascot.height), mh), Image.LANCZOS)

        slot = None
        if overlap_box:
            mx = min(overlap_box[2] - int(mascot.width * 0.62), WIDTH - 50 - mascot.width)
            my = overlap_box[3] - int(mascot.height * 0.42)
            image, pad = self.mascot_overlay(mascot)
            box = (mx - pad, my - pad, mx - pad + image.width, my - pad + image.height)
            slot = {"type": "image", "rect": rel(box), "src": to_data_uri(image, "PNG")}
        else:
            mx = WIDTH - MARGIN - mascot.width + 40
            my = top + (room - mascot.height) // 2

        halo = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        cx, cy, r = mx + mascot.width // 2, my + mascot.height // 2, mascot.width // 2
        ImageDraw.Draw(halo).ellipse((cx - r, cy - r, cx + r, cy + r), fill=self.accent_2 + (120,))
        canvas.alpha_composite(halo.filter(ImageFilter.GaussianBlur(140)))
        if not slot:
            canvas.alpha_composite(mascot, (mx, my))

        lx = (WIDTH - lockup.width) // 2 if slot else MARGIN - 20
        canvas.alpha_composite(lockup, (lx, top + (room - lockup.height) // 2))

        if self.theme.event("tagline"):
            tagline = self.font("display", 104)
            self.gradient_text(canvas, (WIDTH // 2, bottom_line - 110), self.theme.event("tagline"), tagline,
                               tracking=0.08 * 104)

        draw.line((MARGIN, bottom_line, WIDTH - MARGIN, bottom_line), fill=self.line, width=3)
        mono = self.font("mono", 46)
        info_y = bottom_line + 110
        for key, x, anchor, color in (("date", MARGIN, "ls", self.text_muted),
                                      ("place", WIDTH // 2, "ms", self.text_muted),
                                      ("hashtag", WIDTH - MARGIN, "rs", self.accent_3)):
            if self.theme.event(key):
                draw.text((x, info_y), self.theme.event(key), font=mono, fill=color, anchor=anchor)
        return slot

    def template(self, captures):
        canvas = self.base_canvas((WIDTH, HEIGHT))
        self.header(canvas, 250)

        top, gap = 340, 70
        if captures == 4:
            w = (WIDTH - 2 * MARGIN - gap) // 2
            h = int(w * 0.86)
            boxes = [(MARGIN + c * (w + gap), top + r * (h + gap), MARGIN + c * (w + gap) + w, top + r * (h + gap) + h)
                     for r in range(2) for c in range(2)]
        else:
            w = WIDTH - 2 * MARGIN
            h = int(w * 3 / 4)
            boxes = [(MARGIN, top, MARGIN + w, top + h)]

        radius_px = int(RADIUS * min(w, h))
        for box in boxes:
            self.photo_frame(canvas, box, radius_px)
        overlap = captures in self.build.get("mascot_overlap", [1])
        mascot_slot = self.footer(canvas, boxes[-1][3] + 120, boxes[-1] if overlap else None)

        slots = [{"type": "capture", "rect": rel(box), "index": i + 1, "mask": "rounded",
                  "radius": RADIUS, "crop": True} for i, box in enumerate(boxes)]
        if mascot_slot:
            slots.append(mascot_slot)   # after the captures: drawn over the photo
        return {
            "format": "pibooth-template",
            "version": 1,
            "name": "{} ({})".format(self.theme.name, captures),
            "captures": captures,
            "orientation": "portrait",
            "background": {"image": to_data_uri(canvas)},
            "slots": slots,
        }


def rel(box):
    """Pixel box -> normalized [x, y, w, h]."""
    x0, y0, x1, y1 = box
    return [round(x0 / WIDTH, 5), round(y0 / HEIGHT, 5), round((x1 - x0) / WIDTH, 5), round((y1 - y0) / HEIGHT, 5)]


def web_theme(theme):
    """Return the theme of the share web page (plain data)."""
    colors = {name: "#%02X%02X%02X" % theme.color(name)
              for name in ("background", "surface", "surface-raised", "text", "text-dim", "text-muted",
                           "accent", "accent-2", "accent-3", "on-accent", "line")
              if theme.color(name)}
    texts = theme.section("share")
    logo = None
    if theme.asset("logo"):
        image = Image.open(theme.asset("logo")).convert("RGBA")
        image = image.crop(image.getbbox())
        image.thumbnail((480, 480), Image.LANCZOS)
        logo = to_data_uri(image, "PNG")
    return {
        "name": theme.name,
        "event": theme.section("event"),
        "colors": colors,
        "gradient": ["#%02X%02X%02X" % theme.color(c) for c in theme.section("gradients").get("text", [])],
        "web": theme.section("web"),
        "texts": texts.get("texts", {}),
        "logo": logo,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("theme", help="theme name or folder")
    parser.add_argument("--worker", help="write the share web page theme to this JavaScript file")
    options = parser.parse_args()

    theme = themes.load(options.theme)
    if not theme:
        parser.error("theme '{}' not found".format(options.theme))

    style = theme.section("build").get("style")
    if style == "galaxy":
        builder = GalaxyBuilder(theme)
        name = osp.basename(theme.path)
        os.makedirs(osp.join(theme.path, "templates"), exist_ok=True)
        for captures in (4, 1):
            path = osp.join(theme.path, "templates", "{}-{}.json".format(name, captures))
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(builder.template(captures), fp)
            print("Wrote", path, "({} KB)".format(osp.getsize(path) // 1024))
        path = osp.join(theme.path, "assets", "booth-background.jpg")
        builder.booth_background().save(path, "JPEG", quality=90, optimize=True, progressive=True)
        print("Wrote", path)
        for filename, image in (("booth-capture-group.png", builder.booth_capture_group()),
                                ("booth-processing.png", builder.booth_processing())):
            path = osp.join(theme.path, "assets", filename)
            image.save(path, "PNG", optimize=True)
            print("Wrote", path)
    elif style:
        parser.error("unknown build style '{}'".format(style))

    if options.worker:
        with open(options.worker, "w", encoding="utf-8") as fp:
            fp.write("// Generated by tools/build_theme.py from the '{}' theme, do not edit.\n".format(theme.name))
            fp.write("export default ")
            json.dump(web_theme(theme), fp, ensure_ascii=False, indent=2)
            fp.write(";\n")
        print("Wrote", options.worker)


if __name__ == "__main__":
    main()
