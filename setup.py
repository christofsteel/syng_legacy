from setuptools import setup

setup(
    name='syng',
    version='0.8.0',
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
        "flask",
        "flask-sqlalchemy",
        "pytaglib",
        "pyxdg",
        "pafy",
        "youtube-dl"
    ]
)
