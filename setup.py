from setuptools import setup
from syng.appname import appname, version

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
            'syng = syng.main:main'
        ]
    },
    description='',
    include_package_data = True,
    zip_safe = False,
    install_requires = [
        "sqlalchemy",
        "flask",
        "flask-sqlalchemy",
        'flask-basicauth',
        "pytaglib",
        "pyxdg",
        "pafy",
        "youtube-dl"
    ]
)
