from threading import Thread, Event, Lock
import pafy
import os
import sys
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
    def __init__(self, stream, filename, entry, primary=True):
        super().__init__()
        self.stream = stream
        self.filename = filename
        self.primary = primary
        self.entry = entry

    def callback(self, total, downloaded, ratio, rate, eta):
        print(ratio)
        if self.primary:
            if not self.entry.started.is_set() and (ratio > 0.02):
                self.entry.started.set()
            if total == downloaded:
                self.entry.moving.acquire()
        else:
            if not self.entry.secondary_started.is_set() and (ratio > 0.02):
                self.entry.secondary_started.set()
            if total == downloaded:
                self.entry.secondary_moving.acquire()


    def run(self):
        print(f"Start Downloading {self.filename}")
        print(self.stream)
        print(self.stream.url)
        fn = self.stream.download(filepath="/home/christoph/.cache/syng", quiet=False,
                                  callback=self.callback)
        self.entry.path = fn
        if self.primary:
            self.entry.path_video = fn
        else:
            self.entry.path_audio = fn
        print(f"Finished Downloading {self.filename}")
        try:
            self.entry.moving.release()
        except RuntimeError:
            pass
        try:
            self.entry.secondary_moving.release()
        except RuntimeError:
            pass


def yt_cache(entry):
    def str_to_resolution(s):
        return [int(r) for r in s.split('x')]

    entry.started = Event()
    entry.moving = Lock()
    entry.secondary_started = Event()
    entry.secondary_moving = Lock()
    print("Caching")
    yt_song = pafy.new(entry.id)
    yt_song_audio_instance = yt_song.getbestaudio()
    yt_song_video_instance = yt_song.getbest()
    for stream in yt_song.videostreams:
        if str_to_resolution(stream.resolution)[1] > app.max_res or \
                str_to_resolution(yt_song_video_instance.resolution)[1] >= str_to_resolution(stream.resolution)[1]:
            continue
        yt_song_video_instance = stream

    yt_song_instance = yt_song.getbest()

    entry.use_combined = str_to_resolution(yt_song_instance.resolution)[0] >= \
        str_to_resolution(yt_song_video_instance.resolution)[0]

    filename = "%s1.%s" % (yt_song_instance.title, yt_song_instance.extension)
    filename_video = "%s1_video.%s" % (yt_song_video_instance.title, yt_song_video_instance.extension)
    filename_audio = "%s1_audio.%s" % (yt_song_audio_instance.title, yt_song_audio_instance.extension)

    path = os.path.join(app.configuration["youtube"]["cachedir"], filename)
    path_video = os.path.join(app.configuration["youtube"]["cachedir"], filename_video)
    path_audio = os.path.join(app.configuration["youtube"]["cachedir"], filename_audio)

    #try:
    #    if entry.use_combined:
    #        with open(path, 'a'):
    #            pass
    #    else:
    #        with open(path_video, 'a'):
    #            with open(path_audio, 'a'):
    #                pass

    #except FileNotFoundError:
    filename = "%s1.%s" % (entry.id.split("=")[-1], yt_song_instance.extension)
    filename_video = "%s1_video.%s" % (entry.id.split("=")[-1], yt_song_video_instance.extension)
    filename_audio = "%s1_audio.%s" % (entry.id.split("=")[-1], yt_song_audio_instance.extension)
    path = os.path.join(app.configuration["youtube"]["cachedir"], filename)
    path_video = os.path.join(app.configuration["youtube"]["cachedir"], filename_video)
    path_audio = os.path.join(app.configuration["youtube"]["cachedir"], filename_audio)

    if entry.use_combined:
        thread = YTDownloadThread(yt_song_instance, path, entry)
        thread.start()
        #entry.path = path
    else:
        video_thread = YTDownloadThread(yt_song_video_instance, path_video, entry)
        audio_thread = YTDownloadThread(yt_song_audio_instance, path_audio, entry, primary=False)
        video_thread.start()
        audio_thread.start()
        #entry.path_video = path_video
        #entry.path_audio = path_audio
    return entry
