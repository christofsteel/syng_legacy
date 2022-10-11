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

        # split filename into extension and name
        name, ext = os.path.splitext(self.filename)
        ext = ext[1:]

        if "audioext" in app.configuration[ext]:
            mp3_filename = name + "." + app.configuration[ext]["audioext"]
            self.client.fget_object(
                    app.s3_bucket, mp3_filename, os.path.join(app.configuration["s3"]["cachedir"], mp3_filename)
                    )
            print(f"Finished Downloading {mp3_filename}")

        self.client.fget_object(
                app.s3_bucket, self.filename, os.path.join(app.configuration["s3"]["cachedir"], self.filename)
                )
        self.entry.path = os.path.join(app.configuration["s3"]["cachedir"], self.filename)
        print(f"Finished Downloading {self.filename}")
        self.entry.tag()
        self.entry.started.set()
