import time
try:
    from os import scandir, walk
    python35 = True
except ImportError:
    print("You have to install scandir if your python version is below 3.5")
    from scandir import scandir, walk
    python35 = False


from .database import Artists, Songs, Albums
from .id3 import ID3

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

def update(path, db, rwlock):
    time_start = time.time()
    songs = Songs.query.filter(Songs.only_initial == True).all()
    artists = Artists.query.all()
    artists_dict = {artist.name: artist for artist in artists}
    albums = Albums.query.all()
    albums_dict = {album.title: album for album in albums}
    for i, song in enumerate(songs):
        print("Updating: %d/%d" % (i, len(songs)), end="\r")
        try:
            meta = ID3(song.path[:-4] + ".mp3")
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
        except OSError:
            print("Could not find %s, removing it from Library" % (song.path[:-4] + ".mp3"))
            with rwlock.locked_for_write():
                db.session.delete(song)
                db.session.flush()
                if i % 1000 == 0:
                    db.session.commit()
    with rwlock.locked_for_write():
        db.session.commit()
    print("Scan completed in %ss" % round(time.time() - time_start, 1))

def rough_scan(path, db):
    time_start = time.time()
    scanned_files = get_file_list(path)
    query = Songs.query.with_entities(Songs.path).order_by(Songs.path)
    artists = Artists.query.all()
    artists_dict = {artist.name: artist for artist in artists}
    albums = Albums.query.all()
    albums_dict = {album.title: album for album in albums}

    db_files = [a[0] for a in query.all()]
    new_files, deleted_files = get_diff(sorted(scanned_files), db_files)

    new_files_string = "\n".join(new_files)
    deleted_files_string = "\n".join(deleted_files)
    print("New files: \n%s\nDeleted files: \n%s\n" % (new_files_string, deleted_files_string))
    count  = 0
    for file in deleted_files:
        deleted = Songs.query.filter(Songs.path == file).one()
        db.session.delete(deleted)
    for file in new_files:
        count += 1
        try:
            meta = ID3(file[:-4] + ".mp3", True)
            title = meta.title
            album = meta.album
            artist = meta.artist

            db_album = albums_dict[album] if album in albums_dict else Albums(album)
            albums_dict[album] = db_album
            db_artist = artists_dict[artist] if artist in artists_dict else Artists(artist)
            artists_dict[artist] = db_artist

            print("%d/%d" % (count, len(new_files)), end="\r")
            db.session.add(Songs(file, title, 0, 0, db_album, db_artist, True, True))

        except OSError:
            pass

    db.session.commit()
    print("Scan completed in %ss" % round(time.time() - time_start, 1))

def get_file_list(path):
    list = []
    if python35:
        with scandir(path) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.name.endswith('.cdg') and entry.is_file():
                    list.append(entry.path)
                if not entry.name.startswith('.') and entry.is_dir():
                    list.extend(get_file_list(entry.path))
    else:
        it = scandir(path)
        for entry in it:
            if not entry.name.startswith('.') and entry.name.endswith('.cdg') and entry.is_file():
                list.append(entry.path)
            if not entry.name.startswith('.') and entry.is_dir():
                list.extend(get_file_list(entry.path))
    return list
