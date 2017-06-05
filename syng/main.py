from flask import jsonify, request, render_template
import subprocess
from threading import Thread, Lock
import pafy

from .flask_init import app, db, args
from .database import Artists, Songs, Albums
from .synctools import PreviewQueue, locked, ReaderWriterLock
from .scanner import rough_scan, update
from .id3 import ID3
from .appname import appname_pretty, version

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
                meta = ID3(song.path[:-4] + ".mp3")
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

@app.route('/comments', methods=['GET'])
def get_comments():
    song = request.args.get("song")
    with app.rwlock.locked_for_read():
        comments = db.Comments.query.filter(db.Comments.song_id == song).all()
    return jsonify(result = [{'name': comment.name, 'comment': comment.comment} for comment in comments])

@app.route('/comments', methods=['POST'])
def post_comment():
    json = request.get_json(force=True)


@app.route('/query', methods=['GET'])
def query():
    args = request.args
    simple = args.get("simple")
    query = args.get("q")
    title = args.get("title")
    artist = args.get("artist")
    album = args.get("album")
    res = []
    exact = args.get("exact")
    with app.rwlock.locked_for_read():
        if simple:
            title = Songs.query.filter(Songs.title.like("%%%s%%" % query)).all()
            artists = Songs.query.join(Artists.query.filter(Artists.name.like("%%%s%%" % query))).all()
            res = list(set(title + artists))
        else:
            q = Songs.query
            if title is not None:
                if exact:
                    q = q.filter(Songs.title == title)
                else:
                    q = q.filter(Songs.title.like("%%%s%%" % title))
            if album is not None:
                if exact:
                    album = Albums.query.filter(Albums.title == album)
                    q = q.join(album)
                else:
                    album = Albums.query.filter(Albums.title.like("%%%s%%" % album))
                    q = q.join(album)
            if artist is not None:
                if exact:
                    q = q.join(Artists.query.filter(Artists.name == artist))
                else:
                    artist = Artists.query.filter(Artists.name.like("%%%s%%" % artist))
                    q = q.join(artist)
            res = q.all()
    return jsonify(result = [r.to_dict() for r in res], request=request.args)

@app.route('/queue', methods=['GET'])
def get_queue():
    queue = app.queue.get_list()
    return jsonify(current = app.current, queue = queue, last10 = app.last10)

@app.route('/queue', methods=['POST'])
def append_queue():
    json = request.get_json(force=True)
    content = Entry.from_dict(json)
    app.queue.put(content)
    queue = app.queue.get_list()
    return jsonify(current = app.current, queue = queue, last10 = app.last10)

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html", appname=appname_pretty, version=version)


class MPlayerThread(Thread):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def run(self):
        while True:
            app.current = self.app.queue.get()
            print(app.current)
            if app.current['type'] == "library":
                title = app.current.path[:-4]

                #rc = subprocess.run(["cvlc", title + ".cdg", "--input-slave", title + ".mp3"])#, "-audiofile", title + ".mp3"])
                rc = subprocess.run(["mplayer", title + ".cdg","-fs", "-framedrop", "-audiofile", title + ".mp3"])
                #rc = subprocess.run(["bash", "-c", "\"ffmpeg -i %s.cdg -i %s.mp3 -f matroska - | ffplay \"" % (title, title)])
                if rc.returncode != 0:
                    print("ERROR!")
            elif app.current['type'] == "youtube":
                rc = subprocess.run(["mplayer", app.current.path, "-fs", "-framedrop"])
            app.last10 = app.last10[:9]
            app.last10.insert(0,app.current)
            app.current = None





class ScannerThread(Thread):
    def __init__(self, path, db, rwlock):
        super().__init__()
        self.library = path
        self.db = db
        self.rwlock = rwlock

    def run(self):
        update(self.library, self.db, self.rwlock)

def main():
    app.rwlock = ReaderWriterLock()
    app.current = None
    app.last10 = []

    db.create_all()
    if args.scan:
        rough_scan(app.configuration['library']['path'], db) # Initial fast scan
        scannerThread = ScannerThread(app.configuration['library']['path'], db, app.rwlock)
        scannerThread.start()
    app.queue = PreviewQueue()
    mpthread = MPlayerThread(app)
    mpthread.start()
    app.run(port=int(app.configuration['server']['port']), host=app.configuration['server']['host'])


if __name__ == '__main__':
    main()