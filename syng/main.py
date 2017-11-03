import subprocess
from threading import Thread
import shlex
import os.path
from argparse import ArgumentParser

from . import app, db, auth, appname
from .synctools import PreviewQueue, ReaderWriterLock, FakeLock
from .scanner import rough_scan, update
from xdg.BaseDirectory import xdg_config_home



def enquote(string):
    return shlex.quote(string)

def s(string):
    if string:
        return string.replace("\"", "").replace("\'", "").replace("%", "").replace(":","")
    else:
        return ""

class MPlayerThread(Thread):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def run(self):
        while True:
            try:
                app.current = self.app.queue.get()
                if app.preview_performers == True:
                    print("wtf")
                    creation_command = app.configuration["preview"]["generation_command"].format(
                        tmp_file=app.configuration["preview"]["tmp_file"],
                        title=s(app.current["title"]),
                        album=s(app.current["album"]),
                        artist=s(app.current["artist"]),
                        singer=s(app.current["singer"])
                    )
                    print(creation_command)
                    app.process = subprocess.Popen(shlex.split(creation_command))
                    app.process.wait()
                    player = app.configuration['default']['player']
                    if 'player' in app.configuration['preview']:
                        player = app.configuration['preview']['player']

                    playercommand = app.configuration["playback"][player].format(video = app.configuration["preview"]["tmp_file"])
                    app.process = subprocess.Popen(shlex.split(playercommand))
                    app.process.wait()

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
                                                     audio=enquote("%s.%s" % (title, app.configuration[ext]['audioext'])))

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
                    path = app.current.path
                    if app.caching:
                        app.current.started.wait()
                        app.current.moving.acquire()
                        tmp_path = path + ".temp"
                        if os.path.exists(tmp_path):
                            path = tmp_path
                    fullcommand = command.format(video=enquote(path))
                    app.process = subprocess.Popen(shlex.split(fullcommand))
                    app.process.wait()
                    if app.caching:
                        app.current.moving.release()
                    rc = app.process.returncode
                    if rc != 0:
                        print("ERROR!")
                else:
                    print("DOES NOT COMPUTE")
                app.last10 = app.last10[:9]
                app.last10.insert(0,app.current)
                app.current = None
            except:
                pass


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
    app.preview_performers = str(app.configuration['preview']['enabled']).lower() == str(True).lower()
    app.caching = str(app.configuration['youtube']['caching']).lower() == str(True).lower()
    app.channels = [channel.split(':') for channel in app.configuration['youtube']['channels'].split(',')]
    app.only_channels = str(app.configuration['youtube']['mode']).lower() == str("only_channels").lower()
    app.no_channels = str(app.configuration['youtube']['mode']).lower() == str("no_channels").lower() or \
        app.configuration['youtube']['channels'] == ''
    os.makedirs(app.configuration['youtube']['cachedir'], exist_ok=True)

    os.makedirs(os.path.dirname(config), exist_ok=True)
    if not os.path.exists(config):
        with open(config, 'w') as configfile:
            app.configuration.write(configfile)
            print("Created %s" % config)

    if app.configuration["library"]["database"].startswith("sqlite"):
        os.makedirs(os.path.dirname(os.path.abspath(app.configuration['library']['database'][10:])), exist_ok=True)

    #os.makedirs(os.path.abspath(app.configuration['library']['path']), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = app.configuration['library']['database']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'secret!'
    app.config['BASIC_AUTH_USERNAME'] = 'admin'
    app.config['BASIC_AUTH_PASSWORD'] = app.configuration['admin']['password']

    app.extensions = {ext: app.configuration[ext] for ext in app.configuration['library']['filetypes'].split(',')}

    if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres"):
        db.dbtype = "postgres"
    else:
        db.dbtype = "other"


    if app.configuration["library"]["database"].startswith("sqlite"):
        app.rwlock = ReaderWriterLock()
    else:
        app.rwlock = FakeLock()

    db.app = app
    db.init_app(app)
    auth.init_app(app)

    app.current = None
    app.last10 = []

    if db.dbtype == 'postgres':
        db.configure_mappers()
    db.create_all()

    if scan:
        rough_scan(app.configuration['library']['path'], app.extensions, db) # Initial fast scan
        scannerThread = ScannerThread(app.configuration['library']['path'], db, app.extensions, app.rwlock)
        scannerThread.start()
    app.queue = PreviewQueue("/tmp/syng-tmp.json")
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

