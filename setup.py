import sys

from setuptools import setup
from syng.appname import appname, version

deps = [
    "sqlalchemy",
    "flask",
    "flask-sqlalchemy",
    'flask-basicauth',
    "pytaglib",
    "pyxdg",
    "pafy",
    "youtube-dl"
]

if sys.version_info.major == 3 and sys.version_info.minor < 5:
    deps.append("scandir")

setup(
    name=appname,
    version=version,
    packages=['syng'],
    url='https://git.k-fortytwo.de/christofsteel/syng',
    license='GPL3',
    author='Christoph Stahl',
    author_email='christoph.stahl@uni-dortmund.de',
    entry_points= {
        'console_scripts' : [
            'syng = syng.main:main',
            'syng_cli = syng.cli:main'
        ]
    },
    description='',
    include_package_data = True,
    zip_safe = False,
    install_requires = deps
)
