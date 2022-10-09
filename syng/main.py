import subprocess
from threading import Thread
import shlex
import os.path
from argparse import ArgumentParser
import time

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

    def generate_preview(self):
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

    def play_preview(self):
        player = app.configuration['default']['player']
        if 'player' in app.configuration['preview']:
            player = app.configuration['preview']['player']

        playercommand = app.configuration["playback"][player].format(video = app.configuration["preview"]["tmp_file"])
        app.process = subprocess.Popen(shlex.split(playercommand))
        app.process.wait()

    def get_default_player_name(self, ext, split=False):
        player_string = 'player' if not split else 'player_split'
        if player_string in app.configuration[ext]:
            return app.configuration[ext][player_string]
        return app.configuration['default']['player']



    def get_player_command(self, path, type='library', second_path=None):
        if type == 'library':
            title, ext = os.path.splitext(path)
            ext = ext[1:]
            player = self.get_default_player_name(ext)
            command = app.configuration['playback'][player]
            if 'audioext' in app.configuration[ext]:
                return command.format(video=enquote(path),
                                      audio=enquote("%s.%s" % (title, app.configuration[ext]['audioext'])))
            return command.format(video=enquote(path))
        if type == 'youtube':
            split = not second_path is None
            player = self.get_default_player_name('youtube', split)
            command = app.configuration['playback'][player]
            if second_path is None:
                return command.format(video=enquote(path))
            else:
                return command.format(video=enquote(path), audio=enquote(second_path))


    def run(self):
        while True:
            try:
                app.current = self.app.queue.get()
                app.current['starttime'] = int(time.time())
                path = app.current.path
                path_second = None

                if app.preview_performers:
                    self.generate_preview()
                    self.play_preview()
                if app.current['type'] == 'youtube':
                    if not app.current.use_combined:
                        path = app.current.path_video
                        path_second = app.current.path_audio

                    app.current.started.wait()
                    if not app.current.use_combined:
                        app.current.secondary_started.wait()

                    app.current.moving.acquire()
                    if os.path.exists(path + ".temp"):
                        path += ".temp"
                    if not app.current.use_combined:
                        app.current.secondary_moving.acquire()
                        if os.path.exists(path_second + ".temp"):
                            path_second += ".temp"

                play_command = self.get_player_command(path, app.current['type'], path_second)
                print(play_command)
                app.process = subprocess.Popen(shlex.split(play_command))
                app.process.wait()
                if app.current['type'] == 'youtube':
                    app.current.moving.release()
                    if not app.current.use_combined:
                        app.current.secondary_moving.release()
                rc = app.process.returncode
                if rc != 0:
                    print("ERROR!")

                app.current = None
                app.queue._current = None
                app.queue.save_to_file()

                app.last10 = app.last10[:9]
                app.last10.insert(0,app.current)
                app.current = None
            except Exception as e:
                print(e)
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

def init_app(config="{}/{}/{}.config".format(xdg_config_home, appname,appname), scan=False, fastscan=False):
    config = os.path.abspath(config)
    app.configuration.read(config)
    #if args.create_config:
    app.preview_performers = str(app.configuration['preview']['enabled']).lower() == str(True).lower()
    app.channels = app.configuration['youtube']['channels'].split(',')
    app.only_channels = str(app.configuration['youtube']['mode']).lower() == str("only_channels").lower()
    app.max_res = int(app.configuration['youtube']['max_res'])
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

    if scan or fastscan:
        rough_scan(app.configuration['library']['path'], app.extensions, db) # Initial fast scan
        if not fastscan:
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
    parser.add_argument("--scan", '-s', action='store_true', help="scan the library, and update ID3 Tags")
    parser.add_argument("--fast-scan", '-f', action='store_true', help="only scan for files (faster, implies --scan)")
    args = parser.parse_args()
    app = init_app(args.config, args.scan, args.fast_scan)
    app.run(port=int(app.configuration['server']['port']), host=app.configuration['server']['host'], threaded=True, debug=True)

if __name__ == '__main__':
    main()

