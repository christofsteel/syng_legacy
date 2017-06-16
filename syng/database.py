import os

from . import db
from flask_sqlalchemy import BaseQuery
from sqlalchemy_searchable import SearchQueryMixin
from sqlalchemy_utils.types import TSVectorType
from sqlalchemy.ext.compiler import compiles


@compiles(TSVectorType, "sqlite")
def visit_TSVECTOR_sqlite(*args, **kwargs):
    return "STRING"

@compiles(TSVectorType, "mysql")
def visit_TSVECTOR_mysql(*args, **kwargs):
    return "STRING"

class ArtistQuery(BaseQuery, SearchQueryMixin):
    pass

class AlbumsQuery(BaseQuery, SearchQueryMixin):
    pass

class SongsQuery(BaseQuery, SearchQueryMixin):
    pass


class Artists(db.Model):
    query_class = ArtistQuery
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, unique=True)

    def __init__(self, name):
        self.name = name


class Albums(db.Model):
    query_class = AlbumsQuery
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode, unique=True)

    def __init__(self, title):
        self.title = title


class Comments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'))
    name = db.Column(db.Unicode)
    comment = db.Column(db.Unicode)
    song = db.relationship("Songs", backref="comments")


class Songs(db.Model):
    query_class = SongsQuery
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.Unicode, unique=True)
    filename = db.Column(db.Unicode)
    type = db.Column(db.Unicode)
    title = db.Column(db.Unicode)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'))
    album = db.relationship("Albums", backref="songs")
    artist_id = db.Column(db.Integer, db.ForeignKey("artists.id"))
    artist = db.relationship("Artists", backref="songs")
    duration = db.Column(db.Integer)
    noid3 = db.Column(db.Boolean)
    only_initial = db.Column(db.Boolean)
    search_vector = db.Column(TSVectorType('filename'))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'album': self.album.title,
            'artist': self.artist.name,
            'noid3': self.noid3,
            'duration': self.duration
        }

    def __init__(self, path, type, title=None, track=None, duration=0, album=None, artist=None, noid3=False, only_initial=False):
        self.path = path
        self.filename = os.path.basename(path)
        self.type = type
        self.title = title
        self.track = track
        self.album = album
        self.duration = duration
        self.artist = artist
        self.noid3 = noid3
        self.only_initial = only_initial

