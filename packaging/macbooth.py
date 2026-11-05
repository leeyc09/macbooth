"""MacBooth launcher used by the packaged application (see MacBooth.spec).

The plugins of this repository are shipped inside the application and always
loaded from there, so the application works without the source tree.
"""

import multiprocessing
import os
import os.path as osp
import shutil
import sys

BUNDLED_PLUGINS = ('pibooth_r2_upload.py', 'pibooth_picture_template.py',
                   'pibooth_qrcode.py', 'pibooth_clip.py', 'pibooth_factory.py')


def bundle_dir():
    """Return the folder holding the bundled data files."""
    return getattr(sys, '_MEIPASS', osp.dirname(osp.dirname(osp.abspath(__file__))))


def plugin_paths(paths):
    """Replace the configured paths of the bundled plugins by the bundled
    copies and add the bundled plugins not configured yet.
    """
    folder = osp.join(bundle_dir(), 'plugins')
    bundled = {name: osp.join(folder, name) for name in BUNDLED_PLUGINS}
    result = []
    for path in paths:
        name = osp.basename(path)
        result.append(bundled.pop(name, path))
    return result + [bundled[name] for name in BUNDLED_PLUGINS if name in bundled]


def install_config(folder='~/.config/pibooth'):
    """Copy the bundled configuration files missing in the configuration
    folder, so that a new Mac starts with the settings of the build Mac.
    """
    source = osp.join(bundle_dir(), 'config')
    folder = osp.expanduser(folder)
    if not osp.isdir(source) or osp.isfile(osp.join(folder, 'pibooth.cfg')):
        return
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(source):
        if not osp.exists(osp.join(folder, name)):
            shutil.copy2(osp.join(source, name), folder)


def main():
    install_config()
    from pibooth import booth
    from pibooth.plugins import PiPluginManager

    load_all_plugins = PiPluginManager.load_all_plugins

    def load_bundled_plugins(self, paths, disabled=None):
        return load_all_plugins(self, plugin_paths(paths), disabled)

    PiPluginManager.load_all_plugins = load_bundled_plugins
    booth.main()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
