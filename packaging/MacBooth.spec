# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec of the MacBooth application: ``packaging/build_mac.sh``."""

import os
import os.path as osp

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = osp.dirname(SPECPATH)
PLUGINS = ['pibooth_r2_upload', 'pibooth_picture_template', 'pibooth_qrcode',
           'pibooth_clip', 'pibooth_factory']

datas = collect_data_files('pibooth', excludes=['**/*.py', '**/__pycache__'])
datas += collect_data_files('pygame_menu')
datas += collect_data_files('pygame_vkeyboard')
datas += [(osp.join(ROOT, 'plugins', name + '.py'), 'plugins') for name in PLUGINS]
# Configuration staged by build_mac.sh
CONFIG = osp.join(SPECPATH, 'build', 'config')
datas += [(osp.join(CONFIG, name), 'config') for name in sorted(os.listdir(CONFIG))]
# Local pages, without hidden files and folders (.DS_Store, tool state)
for folder, dirs, files in os.walk(osp.join(ROOT, 'factory')):
    dirs[:] = [name for name in dirs if not name.startswith('.')]
    target = osp.relpath(folder, ROOT)
    datas += [(osp.join(folder, name), target) for name in files if not name.startswith('.')]

a = Analysis(
    [osp.join(SPECPATH, 'macbooth.py')],
    pathex=[ROOT, osp.join(ROOT, 'plugins')],
    datas=datas,
    # The plugins are loaded from their path at runtime: analyse them to
    # bundle their dependencies
    hiddenimports=PLUGINS + collect_submodules('pibooth') + ['boto3', 'botocore', 'qrcode'],
    excludes=['tkinter', 'matplotlib', 'IPython', 'pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MacBooth',
    console=False,
    argv_emulation=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name='MacBooth')

app = BUNDLE(
    coll,
    name='MacBooth.app',
    icon=osp.join(SPECPATH, 'build', 'MacBooth.icns'),
    bundle_identifier='dev.droidknights.macbooth',
    info_plist={
        'CFBundleDisplayName': 'MacBooth',
        'CFBundleShortVersionString': '2.1.1',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '12.0',
        'NSCameraUsageDescription': 'MacBooth uses the camera to take the photo booth pictures.',
        'NSLocalNetworkUsageDescription': 'MacBooth serves the remote control and settings pages on the local network.',
    },
)
