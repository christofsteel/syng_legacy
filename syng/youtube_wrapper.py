from threading import Thread, Event, Lock
import pafy
import os
from . import app

def search(q, channel):
    search_query = {
        'q': q,
        'maxResults': min(50,int(app.configuration["query"]["limit_results"])),
        'part': 'id,snippet',
        'type': 'video'
    }
    if channel:
        search_query['channelId']= channel
    print(search_query)
    result = pafy.call_gdata('search', search_query)
    return [
        {
            'id': 'https://www.youtube.com/watch?v=%s' % item['id']['videoId'],
            'album': 'YouTube',
            'artist': item['snippet']['channelTitle'],
            'title': item['snippet']['title']
        } for item in result['items'] if item['id']['kind'] == "youtube#video"]

class YTDownloadThread(Thread):
    def __init__(self, stream, filename, entry):
        super().__init__()
        self.stream = stream
        self.filename = filename
        self.entry = entry

    def callback(self, total, downloaded, ratio, rate, eta):
        if not self.entry.started.is_set() and (ratio > 0.02):
            self.entry.started.set()
        if total == downloaded:
            self.entry.moving.acquire()

    def run(self):
        self.stream.download(filepath=self.filename, quiet=True,
                             callback=self.callback)
        self.entry.moving.release()


def yt_cache(entry):
    entry.started = Event()
    entry.moving = Lock()
    print("Caching")
    yt_song = pafy.new(entry.id)
    yt_song_instance = None
    max_res = 0
    for stream in yt_song.streams:
        print(stream.resolution)
        if stream.resolution.endswith("3D"):
            continue
        try:
            resolution = [int(x) for x in stream.resolution.split('x')]
            if resolution[0] > 1280:
                continue
            if max_res > resolution[0]:
                continue
            max_res = resolution[0]
            yt_song_instance = stream
        except:
            continue

    filename = "%s - [%s].%s" % (yt_song_instance.title, entry.id.split("=")[-1], yt_song_instance.extension)
    path = os.path.join(app.configuration["youtube"]["cachedir"], filename)
    try:
        with open(path, 'w'):
            pass
    except FileNotFoundError:
        filename = "%s.%s" % (entry.id.split("=")[-1], yt_song_instance.extension)
        path = os.path.join(app.configuration["youtube"]["cachedir"], filename)
    thread = YTDownloadThread(yt_song_instance, path, entry)
    thread.start()
    entry.path = path
    return entry
