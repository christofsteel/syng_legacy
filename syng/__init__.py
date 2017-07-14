import configparser
from xdg.BaseDirectory import xdg_data_home, xdg_cache_home

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_searchable import make_searchable
from flask_basicauth import BasicAuth

appname = "syng"
appname_pretty = "sYng"
version = "0.11.3"

app = Flask(__name__)
db = SQLAlchemy()

make_searchable()
auth = BasicAuth()

import syng.database
import syng.views
app.config['SQLALCHEMY_DATABASE_URI'] = None

app.configuration = configparser.ConfigParser()
app.configuration['library'] = {
    'database': "sqlite:///{}/{}/library.db".format(xdg_data_home,appname),
    'path': "{}/{}/songs".format(xdg_data_home, appname),
    'filetypes': 'cdg,mkv'
}
app.configuration['server'] = {
    'port': 1337,
    'host': "0.0.0.0"
}
app.configuration['default'] = {
    'player': 'mplayer',
    'tags': 'filename'
}

app.configuration['cdg'] = {
    'player': 'mplayer_split',
    'audioext': 'mp3',
    'tags': 'both'
}

app.configuration['mkv'] = {
    'tags': 'both'
}

app.configuration['youtube'] = {
    'player': 'mplayer',
    'caching': False,
    'cachedir': '{}/syng'.format(xdg_cache_home)
}

app.configuration['playback'] = {
    'mplayer': 'mplayer {video} -fs -framedrop',
    'mplayer_split': 'mplayer {video} -fs -framedrop -audiofile {audio}'
}
app.configuration['admin'] = {
    'password': 'admin'
}
app.configuration['query'] = {
        'limit_results': 30
        }
