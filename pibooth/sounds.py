# -*- coding: utf-8 -*-

"""Countdown voice ("삼, 이, 일") and shutter sound.

The voice is rendered by the macOS speech synthesizer when the booth starts;
a beep, synthesized at runtime, replaces it elsewhere or until it is ready.
"""

import os.path as osp
import math
import random
import shutil
import tempfile
import threading
import subprocess
from array import array

import pygame

from pibooth.utils import LOGGER

RATE = 44100
PEAK = 32000  # Close to the int16 full scale: these sounds must be heard in a crowd

VOICE = 'Yuna'  # Korean voice of macOS
NUMBERS = ['일', '이', '삼', '사', '오', '육', '칠', '팔', '구', '십']

_SOUNDS = None
_VOICES = {}  # Number -> pygame Sound, filled in the background


def _tone(freq, duration, attack=0.005, release=0.03):
    """Square-ish tone (sine with odd harmonics), louder than a pure sine."""
    count = int(RATE * duration)
    samples = array('h')
    for i in range(count):
        t = i / RATE
        env = min(1.0, t / attack, (duration - t) / release)
        phase = 2 * math.pi * freq * t
        value = math.sin(phase) + math.sin(3 * phase) / 3 + math.sin(5 * phase) / 5
        samples.append(int(PEAK * env * max(-1.0, min(1.0, value * 1.1))))
    return samples


def _click(duration, decay, brightness):
    """Burst of white noise with an exponential decay (mechanical click)."""
    rnd = random.Random(42)
    samples = array('h')
    previous = 0.0
    for i in range(int(RATE * duration)):
        noise = rnd.uniform(-1, 1)
        previous = previous + brightness * (noise - previous)  # Low-pass: lower brightness, duller click
        samples.append(int(PEAK * math.exp(-i / (RATE * decay)) * max(-1.0, min(1.0, previous * 1.6))))
    return samples


def _shutter():
    """Two clicks ("clack-clack") like a camera mirror and shutter."""
    samples = _click(0.06, 0.012, 0.9)
    samples.extend(array('h', [0] * int(RATE * 0.05)))
    samples.extend(_click(0.09, 0.02, 0.6))
    return samples


def _load():
    """Initialize the mixer (released by the window) and build the sounds once."""
    global _SOUNDS
    if _SOUNDS is None:
        _SOUNDS = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            _SOUNDS = {'beep': pygame.mixer.Sound(buffer=_tone(880, 0.18).tobytes()),
                       'last': pygame.mixer.Sound(buffer=_tone(1320, 0.35).tobytes()),
                       'shutter': pygame.mixer.Sound(buffer=_shutter().tobytes())}
            _SOUNDS['beep'].set_volume(0.4)
            _SOUNDS['last'].set_volume(0.4)
        except (pygame.error, NotImplementedError) as ex:
            LOGGER.warning("No sound for the countdown and the capture: %s", ex)
    return _SOUNDS


def _render_voices():
    """Render the numbers with the speech synthesizer (about 0.7s each)."""
    folder = tempfile.mkdtemp(prefix='pibooth-voice-')
    try:
        for number, word in enumerate(NUMBERS, 1):
            path = osp.join(folder, '{}.wav'.format(number))
            subprocess.run(['say', '-v', VOICE, '-o', path, '--file-format=WAVE',
                            '--data-format=LEI16@44100', word],
                           check=True, timeout=10, capture_output=True)
            _VOICES[number] = pygame.mixer.Sound(path)
    except (OSError, subprocess.SubprocessError, pygame.error) as ex:
        LOGGER.warning("No countdown voice, beeps are used: %s", ex)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def preload():
    """Prepare the sounds; the voice is rendered in the background."""
    if _load() and not _VOICES and shutil.which('say'):
        threading.Thread(target=_render_voices, name='voice', daemon=True).start()


def _play(name):
    sound = _load().get(name)
    if sound:
        sound.play()


def countdown(remaining):
    """Say a number of the countdown (beep if there is no voice)."""
    voice = _VOICES.get(remaining)
    if voice:
        voice.play()
    else:
        _play('last' if remaining == 1 else 'beep')


def shutter():
    """Sound of the capture."""
    _play('shutter')
