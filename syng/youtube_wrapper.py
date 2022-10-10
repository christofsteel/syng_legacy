from threading import Thread, Event, Lock
from concurrent.futures import ThreadPoolExecutor
import shlex
import pytube
import os
import urllib.request
import itertools
from . import app


def channelsearch(query, channel):
    browseID = pytube.Channel(f"https://www.youtube.com{channel}").channel_id
    innertube = pytube.innertube.InnerTube(client='WEB')
    endpoint = f'{innertube.base_url}/browse'

    data = {
        'query': query,
        'browseId': browseID,
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


def search_all_channels(args):
    results = []
    approx_results = []

    with ThreadPoolExecutor(max_workers=5) as p:
        thread_results = p.map(lambda c: search(args, c), app.channels + [None])

    for result in thread_results:
        res, approx_res = result
        results += res
        approx_results += approx_res

    return results + approx_results


def contains_index(query, author, title):
    result = author + " " + title
    hit = 0
    queries = shlex.split(query.lower())
    for word in queries:
        if word in result.lower():
            hit += 1

    return hit / len(queries)


def search(args, channel):
    query = args.get("q")
    results = []

    if channel:
        if channel in args and args[channel] == 'true':
            print(f"Searching channel {channel} with query \"{query}\"")
            results = channelsearch(query, channel)
    else:
        if args["append-karaoke"] == 'true':
            query += " karaoke"
        if args["youtube"] == 'true':
            print(f"Searching youtube with query \"{query}\"")
            results = pytube.Search(query).results

    metadatas = [
            {
                'type': 'youtube',
                'id': item.watch_url,
                'album': 'YouTube',
                'artist': item.author,
                'title': item.title,
                'contains_index': contains_index(query, item.author, item.title)
            } for item in results]
    # split into exact and approximate matches
    exact = [item for item in metadatas if item['contains_index'] == 1]
    approx = [item for item in metadatas if item['contains_index'] < 1]

    # sort approx by contains_index
    approx.sort(key=lambda x: x['contains_index'], reverse=True)

    return list(exact), list(approx)


class YTDownloadThread(Thread):
    def __init__(self, stream, filename, entry, primary=True):
        super().__init__()
        self.stream = stream
        self.filename = filename
        self.primary = primary
        self.entry = entry

    def run(self):
        print(f"Start Downloading {self.filename}")
        self.stream.download(filename=self.filename, output_path=app.configuration["youtube"]["cachedir"])
        print(f"Finished Downloading {self.filename}")
        if self.primary:
            try:
                if not self.entry.started.is_set():
                    self.entry.started.set()
            except RuntimeError:
                pass
        else:
            try:
                if not self.entry.secondary_started.is_set():
                    self.entry.secondary_started.set()
            except RuntimeError:
                pass


def yt_cache(entry):
    def str_to_resolution(s):
        if s is not None:
            return int(s[:-1])
        return 0

    entry.started = Event()
    entry.secondary_started = Event()
    print("Caching")
    yt_song = pytube.YouTube(entry.id, on_progress_callback=entry.progress_callback())
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
        thread = YTDownloadThread(yt_song_progressive_instance, filename, entry)
        thread.start()
        entry.path = path
    else:
        audio_thread = YTDownloadThread(yt_song_audio_instance, filename_audio, entry, primary=False)
        video_thread = YTDownloadThread(yt_song_video_instance, filename_video, entry)
        audio_thread.start()
        video_thread.start()
        entry.path_video = path_video
        entry.path_audio = path_audio
    return entry
