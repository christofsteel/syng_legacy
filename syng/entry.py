import pafy

from . import app
from .database import Songs
from .tags import Tags

class Entry(dict):
    def __init__(self, id, singer, type="library"):
        super().__init__()
        self.id = id
        self['id'] = id
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

