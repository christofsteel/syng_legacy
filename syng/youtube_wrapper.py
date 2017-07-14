from threading import Thread, Event, Lock
import pafy
import os
from . import app

def search(q):
    result = pafy.call_gdata('search', {
        'q': q,
        'maxResults': min(50,int(app.configuration["query"]["limit_results"])),
        'part': 'id,snippet',
        'type': 'video'
    })
    return [
        {
            'id': 'https://www.youtube.com/watch?v=%s' % item['id']['videoId'],
            'album': 'YouTube',
            'artist': item['snippet']['channelTitle'],
            'title': item['snippet']['title']
        } for item in result['items']]

class YTDownloadThread(Thread):
    def __init__(self, stream, filename, entry):
        super().__init__()
        self.stream = stream
        self.filename = filename
        self.entry = entry

    def callback(self, total, downloaded, ratio, rate, eta):
        if not self.entry.started.is_set() and (ratio > 0.05):
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
    yt_song_instance = yt_song.getbest()
    path = os.path.join(app.configuration["youtube"]["cachedir"], "%s.%s" % (yt_song_instance.title, yt_song_instance.extension))
    thread = YTDownloadThread(yt_song_instance, path, entry)
    thread.start()
    entry.path = path
    return entry