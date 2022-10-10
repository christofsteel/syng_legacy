import time
import sys
import os.path

from os import scandir, walk

from .tags import Tags
from .database import Songs, Artists, Albums


def get_diff(new, old):
    new_pointer = 0
    old_pointer = 0
    diff_new = []
    diff_old = []
    while new_pointer < len(new) and old_pointer < len(old):
        if new[new_pointer] == old[old_pointer]:
            new_pointer = new_pointer + 1
            old_pointer = old_pointer + 1
        elif new[new_pointer] < old[old_pointer]:
            diff_new.append(new[new_pointer])
            new_pointer = new_pointer + 1
        elif new[new_pointer] > old[old_pointer]:
            diff_old.append(old[old_pointer])
            old_pointer = old_pointer + 1
    if new_pointer < len(new):
        diff_new.extend(new[new_pointer:])
    if old_pointer < len(old):
        diff_old.extend(old[old_pointer:])
    return diff_new, diff_old


def update(path, db, extensions, rwlock):
    time_start = time.time()
    songs = Songs.query.filter(Songs.only_initial == True).all()
    artists = Artists.query.all()
    artists_dict = {artist.name: artist for artist in artists}
    albums = Albums.query.all()
    albums_dict = {album.title: album for album in albums}
    for i, song in enumerate(songs):
        print("Updating: %d/%d" % (i, len(songs)), end="\r")
        tagext = song.type
        if 'audioext' in extensions[song.type]:
            tagext = extensions[song.type]['audioext']
        meta = Tags("%s.%s" % (os.path.splitext(song.path)[0], tagext))
        song.title = meta.title

        db_album = albums_dict[meta.album] if meta.album in albums_dict else Albums(meta.album)
        albums_dict[meta.album] = db_album
        db_artist = artists_dict[meta.artist] if meta.artist in artists_dict else Artists(meta.artist)
        artists_dict[meta.artist] = db_artist
        song.album = db_album
        song.artist = db_artist
        song.only_initial = False
        song.noid3 = meta.noid3
        song.duration = meta.duration
        with rwlock.locked_for_write():
            db.session.add(song)
            db.session.flush()
            if i % 1000 == 0:
                db.session.commit()
            # with rwlock.locked_for_write():
            #    db.session.delete(song)
            #    db.session.flush()
            #    if i % 1000 == 0:
            #        db.session.commit()
    with rwlock.locked_for_write():
        db.session.commit()
    print("Scan completed in %ss" % round(time.time() - time_start, 1))


def make_song_object(path, location, albums_dict, artists_dict):
    filename, extension = os.path.splitext(path)
    extension = extension[1:]

    meta = Tags(path, True)
    title = meta.title
    album = meta.album
    artist = meta.artist

    db_album = albums_dict[album] if album in albums_dict else Albums(album)
    albums_dict[album] = db_album
    db_artist = artists_dict[artist] if artist in artists_dict else Artists(artist)
    artists_dict[artist] = db_artist

    try:
        bytes(path, 'utf-8')
        return Songs(path, extension, title, 0, 0, db_album, db_artist, True, True, location=location)
    except UnicodeError:
        print(f"Cannot convert {path} to unicode", file=sys.stderr)


def rough_scan(path, s3_client, s3_bucket, s3_prefix, extensions, db):
    time_start = time.time()
    scanned_files = get_file_list(path, extensions)
    print("Initial local scan completed in %ss" % round(time.time() - time_start, 1))
    artists = Artists.query.all()
    artists_dict = {artist.name: artist for artist in artists}
    albums = Albums.query.all()
    albums_dict = {album.title: album for album in albums}
    new_s3_songs = []

    if s3_client is not None:
        time_start = time.time()
        s3_files = s3_client.list_objects(bucket_name=s3_bucket, prefix=s3_prefix, recursive=True)
        s3_files = [obj.object_name for obj in s3_files if os.path.splitext(obj.object_name)[1][1:] in extensions.keys()]
        print("Initial S3 scan completed in %ss" % round(time.time() - time_start, 1))
        s3_query = Songs.query.filter_by(location='s3').with_entities(Songs.path).order_by(Songs.path)
        s3_db_files = [row[0] for row in s3_query.all()]
        new_s3_files, old_s3_files = get_diff(s3_files, s3_db_files)
        new_s3_songs = [make_song_object(path, 's3', albums_dict, artists_dict) for path in new_s3_files]

    time_start = time.time()
    query = Songs.query.filter_by(location='local').with_entities(Songs.path).order_by(Songs.path)

    db_files = [a[0] for a in query.all()]
    new_files, deleted_files = get_diff(sorted(scanned_files), sorted(db_files))
    new_songs = [make_song_object(path, 'local', albums_dict, artists_dict) for path in new_files]

    print("Internal Update completed in %ss" % round(time.time() - time_start, 1))

    for file in deleted_files:
        deleted = Songs.query.filter(Songs.path == file).one()
        db.session.delete(deleted)

    amount_of_songs = len(new_songs) + len(new_s3_songs)
    for i, song in enumerate(new_songs + new_s3_songs):
        print(f"{i}/{amount_of_songs}", end="\r")
        db.session.add(song)

    db.session.commit()
    print("Scan completed in %ss" % round(time.time() - time_start, 1))


def get_file_list(path, extensions):
    list = []
    it = scandir(path)
    for entry in it:
        if not entry.name.startswith('.'):
            if entry.is_dir():
                list.extend(get_file_list(entry.path, extensions))
            else:
                if os.path.splitext(entry.name)[1][1:] in extensions.keys() and entry.is_file():
                    list.append(entry.path)
    return list
