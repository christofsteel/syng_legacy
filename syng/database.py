from .flask_init import db

class Artists(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)

    def __init__(self, name):
        self.name = name


class Albums(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True)

    def __init__(self, title):
        self.title = title


class Comments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'))
    name = db.Column(db.String)
    comment = db.Column(db.String)
    song = db.relationship("Songs", backref="comments")


class Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String, unique=True)
    type = db.Column(db.String)
    title = db.Column(db.String)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'))
    album = db.relationship("Albums", backref="songs")
    artist_id = db.Column(db.Integer, db.ForeignKey("artists.id"))
    artist = db.relationship("Artists", backref="songs")
    duration = db.Column(db.Integer)
    noid3 = db.Column(db.Boolean)
    only_initial = db.Column(db.Boolean)

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
        self.type = type
        self.title = title
        self.track = track
        self.album = album
        self.duration = duration
        self.artist = artist
        self.noid3 = noid3
        self.only_initial = only_initial

