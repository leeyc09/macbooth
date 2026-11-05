#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from io import open
import os.path as osp
from setuptools import setup, find_packages


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
import pibooth  # nopep8 : import shall be done after adding setup to paths


def main():
    setup(
        name=pibooth.__name__,
        version=pibooth.__version__,
        description=pibooth.__doc__,
        long_description=open(osp.join(HERE, 'README.md'), encoding='utf-8').read(),
        long_description_content_type='text/markdown',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Other Environment',
            'Intended Audience :: Developers',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved :: MIT License',
            'Operating System :: MacOS :: MacOS X',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Programming Language :: Python :: 3.13',
            'Natural Language :: Danish',
            'Natural Language :: Dutch',
            'Natural Language :: English',
            'Natural Language :: French',
            'Natural Language :: German',
            'Natural Language :: Hungarian',
            'Natural Language :: Italian',
            'Natural Language :: Korean',
            'Natural Language :: Norwegian',
            'Natural Language :: Portuguese',
            'Natural Language :: Portuguese (Brazilian)',
            'Natural Language :: Spanish',
            'Natural Language :: Swedish',
            'Topic :: Multimedia :: Graphics :: Capture :: Digital Camera',
        ],
        # Fork of pibooth (https://github.com/pibooth/pibooth) by Vincent Verdeil, Antoine Rousseaux
        author="Vincent Verdeil, Antoine Rousseaux, leeyc09",
        url="https://github.com/leeyc09/macbooth",
        license='MIT license',
        platforms=['macos'],
        keywords=[
            'macOS',
            'camera',
            'photobooth'
        ],
        packages=find_packages(),
        package_data={
            'pibooth.fonts': ['*.ttf'],
            'pibooth.pictures': ['*/*.png'],
            'pibooth': ['*.ini', 'themes/*/theme.json', 'themes/*/fonts/*', 'themes/*/assets/*',
                        'themes/*/assets/*/*', 'themes/*/templates/*.json'],
        },
        include_package_data=True,
        python_requires=">=3.10",
        install_requires=[
            'Pillow>=10.4.0',
            'pygame>=1.9.6',
            'pygame-menu>=4.0,<5',
            'pygame-vkeyboard>=2.0.8',
            'psutil>=5.5.1',
            'pluggy>=0.13.1',
        ],
        extras_require={
            'dslr': ['gphoto2>=2.0.0'],
            'printer': ['pycups>=1.9.73', 'pycups-notify>=0.0.4'],
            # Webcam (built-in camera, iPhone Continuity Camera, ...)
            'webcam': ['opencv-python-headless>=4.5',
                       # To list the webcams by name on macOS
                       'pyobjc-framework-AVFoundation ; sys_platform == "darwin"'],
            # Upload the final pictures to a Cloudflare R2 bucket (plugins/pibooth_r2_upload.py)
            'r2': ['boto3>=1.26'],
        },
        zip_safe=False,  # Don't install the lib as an .egg zipfile
        entry_points={'console_scripts': ["pibooth = pibooth.booth:main",
                                          "pibooth-count = pibooth.scripts.count:main",
                                          "pibooth-diag = pibooth.scripts.diagnostic:main",
                                          "pibooth-fonts = pibooth.scripts.fonts:main",
                                          "pibooth-regen = pibooth.scripts.regenerate:main",
                                          "pibooth-printcfg = pibooth.scripts.printer:main"]},
    )


if __name__ == '__main__':
    main()
