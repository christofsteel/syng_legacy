import configparser
from xdg.BaseDirectory import xdg_data_home, xdg_cache_home

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_searchable import make_searchable
from flask_basicauth import BasicAuth

appname = "syng"
appname_pretty = "sYng"
version = "0.13.0"

app = Flask(__name__)
db = SQLAlchemy()

make_searchable()
auth = BasicAuth()

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

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
    'caching': True,
    'cachedir': '{}/syng'.format(xdg_cache_home),
    'mode': "normal",
    'channels': ""
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
app.configuration['preview'] = {
    'enabled': True,
    'player': 'mplayer',
    'generation_command': "ffmpeg -y -f lavfi -i color=c=black:s=1920x1080:d=3 -vf \"drawtext=fontcolor=white:fontsize=30:x=(w-text_w)/2:y=(h-text_h-text_h-text_h)/2:text='{artist} - {title}',drawtext=fontcolor=white:fontsize=30:x=(w-text_w)/2:y=(h-text_h)/2:text='{singer}'\" {tmp_file}",
    'tmp_file': '/tmp/syng-preview.mp4'
}
