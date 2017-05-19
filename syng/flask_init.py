import os
import sys
import configparser
from argparse import ArgumentParser
from xdg.BaseDirectory import xdg_data_home, xdg_config_home

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from .appname import appname

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = None


parser = ArgumentParser()
parser.add_argument('--config', '-c', help="configuration file", default="{}/{}/{}.config".format(xdg_config_home, appname,appname))
parser.add_argument("--create-config", "-C", action="store_true", help="create only the configuration file", default=False)
parser.add_argument("--scan", '-s', action='store_true', help="scan the library")
args = parser.parse_args()

args.config = os.path.abspath(args.config)

app.configuration = configparser.ConfigParser()
app.configuration['library'] = {
    'database': "sqlite:///{}/{}/library.db".format(xdg_data_home,appname),
    'path': "{}/{}/songs".format(xdg_data_home, appname)
}
app.configuration['server'] = {
    'port': 1337,
    'host': "0.0.0.0"
}
app.configuration.read(args.config)
if args.create_config:
    os.makedirs(os.path.dirname(args.config), exist_ok=True)
    with open(args.config, 'w') as configfile:
        app.configuration.write(configfile)
        print("Created %s" % args.config)
        sys.exit(0)
    sys.exit(1)

if app.configuration["library"]["database"].startswith("sqlite"):
    os.makedirs(os.path.dirname(os.path.abspath(app.configuration['library']['database'][10:])), exist_ok=True)

os.makedirs(os.path.abspath(app.configuration['library']['path']), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = app.configuration['library']['database']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret!'

db = SQLAlchemy(app)
