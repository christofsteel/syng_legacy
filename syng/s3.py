from threading import Thread
import os

from . import app


class S3DownloadThread(Thread):
    def __init__(self, client, entry):
        super().__init__()
        self.client = client
        self.filename = entry.path
        self.entry = entry

    def run(self):
        print(f"Start Downloading {self.filename}")
        audiofile = self.filename[:-4] + ".mp3"
        self.client.fget_object("karaoke-files", self.filename,
                                os.path.join(app.configuration["s3"]["cachedir"], self.filename))
        self.client.fget_object("karaoke-files", audiofile,
                                os.path.join(app.configuration["s3"]["cachedir"], audiofile))
        self.entry.path = os.path.join(app.configuration["s3"]["cachedir"], self.filename)
        print(f"Finished Downloading {self.filename}")
        self.entry.tag()
        self.entry.started.set()
