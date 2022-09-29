from threading import Thread, Event, Lock
import shlex
import pytube
import os
import urllib.request
from . import app


def channelsearch(query, channel):
    innertube = pytube.innertube.InnerTube(client='WEB')
    endpoint = f'{innertube.base_url}/browse'

    data = {
        'query': query,
        'browseId': channel,
        'params': 'EgZzZWFyY2g%3D'
            }
    data.update(innertube.base_data)
    results = innertube._call_api(endpoint, innertube.base_params, data)
    items = results["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][-1]["expandableTabRenderer"]["content"]["sectionListRenderer"]["contents"]

    list_of_videos = []
    for item in items:
        try:
            if "itemSectionRenderer" in item and "videoRenderer" in item["itemSectionRenderer"]["contents"][0]:
                yt_url = "https://youtube.com/watch?v=" + item["itemSectionRenderer"]["contents"][0]["videoRenderer"]["videoId"]
                author=item["itemSectionRenderer"]["contents"][0]["videoRenderer"]["ownerText"]["runs"][0]["text"]
                title = item["itemSectionRenderer"]["contents"][0]["videoRenderer"]["title"]["runs"][0]["text"]
                yt = pytube.YouTube(yt_url)
                yt.author = author
                yt.title = title
                list_of_videos.append(yt)

        except KeyError:
            pass
    return list_of_videos


def search(q, channel):
    def contains_index(r):
        result = r['artist'] + " " + r['title']
        hit = 0
        queries = shlex.split(q.lower())
        for word in queries:
            if word in result.lower():
                hit += 1

        print(f"{q.lower()} -> {result.lower()} : {100 * hit/len(queries)}%")
        return hit / len(queries)

    if channel:
        results = channelsearch(q, channel)
    else:
        results = pytube.Search(q).results
    
    l= [
            {
                'type': 'youtube',
                'id': item.watch_url,
                'album': 'YouTube',
                'artist': item.author,
                'title': item.title
            } for item in results]
    l.sort(key = contains_index, reverse=True)
    return l


class YTDownloadThread(Thread):
    def __init__(self, stream, filename, entry, primary=True):
        super().__init__()
        self.stream = stream
        self.filename = filename
        self.primary = primary
        self.entry = entry

    def callback(self, total, downloaded, ratio, rate, eta):
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

    def callback2(self, chunknr, maxchunk, total):
        downloaded = chunknr * maxchunk
        ratio = downloaded / total
        if self.primary:
            if not self.entry.started.is_set() and (ratio > 0.02):
                self.entry.started.set()
        else:
            if not self.entry.secondary_started.is_set() and (ratio > 0.02):
                self.entry.secondary_started.set()

    def run(self):
        print(f"Start Downloading {self.filename}")
        print(self.stream)
        print(self.stream.url)
        urllib.request.urlretrieve(self.stream.url, filename=self.filename, reporthook=self.callback2)
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
        if s is not None:
            return int(s[:-1])
        return 0

    entry.started = Event()
    entry.moving = Lock()
    entry.secondary_started = Event()
    entry.secondary_moving = Lock()
    print("Caching")
    yt_song = pytube.YouTube(entry.id)
    yt_song_audio_instance = yt_song.streams.get_audio_only()
    yt_song_video_instance_list = yt_song.streams.filter(adaptive=True).order_by("resolution").desc()
    for stream in yt_song_video_instance_list:
        if str_to_resolution(stream.resolution) > app.max_res:
            continue
        yt_song_video_instance = stream
        break

    yt_song_progressive_instance_list = yt_song.streams.filter(progressive=True).order_by("resolution").desc()
    for stream in yt_song_progressive_instance_list:
        if str_to_resolution(stream.resolution) > app.max_res:
            continue
        yt_song_progressive_instance = stream
        break

    entry.use_combined = str_to_resolution(yt_song_progressive_instance.resolution) >= \
        str_to_resolution(yt_song_video_instance.resolution)

    filename = yt_song_progressive_instance.default_filename
    filename_video = f"video_{yt_song_video_instance.default_filename}"
    filename_audio = f"audio_{yt_song_audio_instance.default_filename}"

    path = os.path.join(app.configuration["youtube"]["cachedir"], filename)
    path_video = os.path.join(app.configuration["youtube"]["cachedir"], filename_video)
    path_audio = os.path.join(app.configuration["youtube"]["cachedir"], filename_audio)

    try:
        if entry.use_combined:
            with open(path, 'a'):
                pass
        else:
            with open(path_video, 'a'):
                with open(path_audio, 'a'):
                    pass

    except FileNotFoundError:
        filename = "%s.%s" % (entry.id.split("=")[-1], os.path.splitext(filename)[1])
        filename_video = "%s_video.%s" % (entry.id.split("=")[-1], os.path.splitext(filename_video)[1])
        filename_audio = "%s_audio.%s" % (entry.id.split("=")[-1], os.path.splitext(filename_audio)[1])
        path = os.path.join(app.configuration["youtube"]["cachedir"], filename)
        path_video = os.path.join(app.configuration["youtube"]["cachedir"], filename_video)
        path_audio = os.path.join(app.configuration["youtube"]["cachedir"], filename_audio)

    if entry.use_combined:
        thread = YTDownloadThread(yt_song_progressive_instance, path, entry)
        thread.start()
        entry.path = path
    else:
        video_thread = YTDownloadThread(yt_song_video_instance, path_video, entry)
        audio_thread = YTDownloadThread(yt_song_audio_instance, path_audio, entry, primary=False)
        video_thread.start()
        audio_thread.start()
        entry.path_video = path_video
        entry.path_audio = path_audio
    return entry
