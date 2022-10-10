from threading import Event

import pytube

from . import app, db
from .s3 import S3DownloadThread
from .database import Songs
from .tags import Tags
from .youtube_wrapper import yt_cache


def add_to_queue(item, queue):
    content = Entry.from_dict(item)
    if content['type'] == 'youtube':
        content = yt_cache(content)
    elif content['location'] == 's3':
        S3DownloadThread(app.s3_client, content).start()

    queue.put(content)


class Entry(dict):
    def __init__(self, id, singer, type="library", location='local'):
        super().__init__()
        self.id = id
        self.started = Event()
        self['id'] = id
        self['singer'] = singer
        self['type'] = type
        self.use_combined = True
        if type == "library":
            self['location'] = location
            with app.rwlock.locked_for_read():
                song = Songs.query.filter(Songs.id == id).one_or_none()
            if song is not None:
                self['title'] = song.title
                self['artist'] = song.artist.name
                self['album'] = song.album.title
                self['duration'] = song.duration
                self['ext'] = song.type
                if 'audioext' in app.extensions[song.type]:
                    self['ext'] = app.extensions[song.type]['audioext']
                self.path = song.path
            if song.only_initial and self['location'] == 'local':
                meta = Tags("%s.%s" % (song.path[:-4], self['ext']))
                self['title'] = meta.title
                self['artist'] = meta.artist
                self['album'] = meta.album
                self['duration'] = meta.duration
                song.only_initial = False
                song.title = meta.title
                song.artist = meta.artist
                song.album = meta.album
                song.duration = meta.duration

        elif type == "youtube":
            song = pytube.YouTube(id)
            self['title'] = song.title
            self['artist'] = song.author
            self['album'] = "YouTube"
            self.path = song.streams.get_highest_resolution().url
            self['duration'] = song.length

    def tag(self):
        meta = Tags("%s.%s" % (self.path[:-4], self['ext']))
        self['title'] = meta.title
        self['artist'] = meta.artist
        self['album'] = meta.album
        self['duration'] = meta.duration

    def from_dict(d):
        if 'type' not in d:
            d['type'] = "library"
        if 'location' not in d:
            d['location'] = None
        return Entry(d['id'], d['singer'], d['type'], d['location'])

    def progress_callback(self):
        def callback(stream, chunk, bytes_remaining):
            ratio = (stream.filesize - bytes_remaining) / stream.filesize
            if stream.includes_video_track:
                if not self.started.is_set() and (ratio > 0.02):
                    self.started.set()
            else:
                if not self.secondary_started.is_set() and (bytes_remaining == 0):
                    self.secondary_started.set()

        return callback
