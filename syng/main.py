import subprocess
from threading import Thread
import pafy
import shlex
import os.path
from argparse import ArgumentParser

from . import app, db, auth, appname
from .database import Songs
from .synctools import PreviewQueue, ReaderWriterLock, FakeLock
from .scanner import rough_scan, update
from .tags import Tags
from xdg.BaseDirectory import xdg_config_home

class Entry(dict):
    def __init__(self, id, singer, type="library"):
        super().__init__()
        self.id = id
        self['singer'] = singer
        self['type'] = type
        if type == "library":
            with app.rwlock.locked_for_read():
                song = Songs.query.filter(Songs.id == id).one_or_none()
            if song is not None:
                self['title'] = song.title
                self['artist'] = song.artist.name
                self['album'] = song.album.title
                self['duration'] = song.duration
                self.path = song.path
            if song.only_initial:
                tagext = song.type
                if 'audioext' in app.extensions[song.type]:
                    tagext = app.extensions[song.type]['audioext']
                meta = Tags("%s.%s" % (song.path[:-4], tagext))
                self['title'] = meta.title
                self['artist'] = meta.artist
                self['album'] = meta.album
                self['duration'] = meta.duration
        elif type == "youtube":
            song = pafy.new(id)
            self['title'] = song.title
            self['artist'] = song.author
            self['album'] = "YouTube"
            self.path = song.getbest().url
            self['duration'] = song.length

    def from_dict(d):
        if not 'type' in d:
            d['type'] = "library"
        return Entry(d['id'], d['singer'], d['type'])


def enquote(string):
    return "\"%s\"" % string

class MPlayerThread(Thread):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def run(self):
        while True:
            app.current = self.app.queue.get()
            print(app.current)
            if app.current['type'] == "library":
                title, ext = os.path.splitext(app.current.path)
                ext = ext[1:]
                player = app.configuration['default']['player']
                if 'player' in app.configuration[ext]:
                    player = app.configuration[ext]['player']

                command = app.configuration['playback'][player]
                try:
                    fullcommand = command.format(video=enquote(app.current.path))
                except KeyError:
                    fullcommand = command.format(video=enquote(app.current.path),
                                                 audio="\"%s.%s\"" % (title, app.configuration[ext]['audioext']))

                app.process = subprocess.Popen(shlex.split(fullcommand))
                app.process.wait()
                rc = app.process.returncode
                if rc != 0:
                    print("ERROR!")
            elif app.current['type'] == "youtube":
                player = app.configuration['default']['player']
                if 'player' in app.configuration['youtube']:
                    player = app.configuration['youtube']['player']
                command = app.configuration['playback'][player]
                fullcommand = command.format(video=enquote(app.current.path))
                app.process = subprocess.Popen(shlex.split(fullcommand))
                app.process.wait()
                rc = app.process.returncode
                if rc != 0:
                    print("ERROR!")
            else:
                print("DOES NOT COMPUTE")
            app.last10 = app.last10[:9]
            app.last10.insert(0,app.current)
            app.current = None


class ScannerThread(Thread):
    def __init__(self, path, db, extensions, rwlock):
        super().__init__()
        self.library = path
        self.db = db
        self.extensions = extensions
        self.rwlock = rwlock

    def run(self):
        update(self.library, self.db, self.extensions, self.rwlock)

def init_app(config="{}/{}/{}.config".format(xdg_config_home, appname,appname), scan=False):
    config = os.path.abspath(config)
    app.configuration.read(config)
    #if args.create_config:
    os.makedirs(os.path.dirname(config), exist_ok=True)
    if not os.path.exists(config):
        with open(config, 'w') as configfile:
            app.configuration.write(configfile)
            print("Created %s" % config)

    if app.configuration["library"]["database"].startswith("sqlite"):
        os.makedirs(os.path.dirname(os.path.abspath(app.configuration['library']['database'][10:])), exist_ok=True)

    os.makedirs(os.path.abspath(app.configuration['library']['path']), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = app.configuration['library']['database']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'secret!'
    app.config['BASIC_AUTH_USERNAME'] = 'admin'
    app.config['BASIC_AUTH_PASSWORD'] = app.configuration['admin']['password']

    app.extensions = {ext: app.configuration[ext] for ext in app.configuration['library']['filetypes'].split(',')}


    if app.configuration["library"]["database"].startswith("sqlite"):
        app.rwlock = ReaderWriterLock()
    else:
        app.rwlock = FakeLock()

    db.app = app
    db.init_app(app)
    auth.init_app(app)

    app.current = None
    app.last10 = []

    db.configure_mappers()
    db.create_all()

    if scan:
        rough_scan(app.configuration['library']['path'], app.extensions, db) # Initial fast scan
        scannerThread = ScannerThread(app.configuration['library']['path'], db, app.extensions, app.rwlock)
        scannerThread.start()
    app.queue = PreviewQueue()
    mpthread = MPlayerThread(app)
    mpthread.start()
    return app

def main():
    parser = ArgumentParser()
    parser.add_argument('--config', '-c', help="configuration file", default="{}/{}/{}.config".format(xdg_config_home, appname,appname))
    #parser.add_argument("--create-config", "-C", action="store_true", help="create only the configuration file", default=False)
    parser.add_argument("--scan", '-s', action='store_true', help="scan the library")
    args = parser.parse_args()
    app = init_app(args.config, args.scan)
    app.run(port=int(app.configuration['server']['port']), host=app.configuration['server']['host'], threaded=True)

if __name__ == '__main__':
    main()

