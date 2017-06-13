import os
import sys
import configparser
from argparse import ArgumentParser
from xdg.BaseDirectory import xdg_data_home, xdg_config_home

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_basicauth import BasicAuth

from .appname import appname

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = None


parser = ArgumentParser()
parser.add_argument('--config', '-c', help="configuration file", default="{}/{}/{}.config".format(xdg_config_home, appname,appname))
#parser.add_argument("--create-config", "-C", action="store_true", help="create only the configuration file", default=False)
parser.add_argument("--scan", '-s', action='store_true', help="scan the library")
args = parser.parse_args()

args.config = os.path.abspath(args.config)

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
    'player': 'mplayer'
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
app.configuration.read(args.config)
#if args.create_config:
os.makedirs(os.path.dirname(args.config), exist_ok=True)
if not os.path.exists(args.config):
    with open(args.config, 'w') as configfile:
        app.configuration.write(configfile)
        print("Created %s" % args.config)

if app.configuration["library"]["database"].startswith("sqlite"):
    os.makedirs(os.path.dirname(os.path.abspath(app.configuration['library']['database'][10:])), exist_ok=True)

os.makedirs(os.path.abspath(app.configuration['library']['path']), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = app.configuration['library']['database']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret!'
app.config['BASIC_AUTH_USERNAME'] = 'admin'
app.config['BASIC_AUTH_PASSWORD'] = app.configuration['admin']['password']


db = SQLAlchemy(app)
extensions = {ext: app.configuration[ext] for ext in app.configuration['library']['filetypes'].split(',')}
auth = BasicAuth(app)
