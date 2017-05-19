import os
import sys
import taglib

useBuildin = False

class ID3:
    def __init__(self, name, noid3=False):
        splitfile = os.path.basename(name[:-4]).split(" - ")
        if noid3:
            try:
                self.noid3 = True
                self.artist = splitfile[0].strip()
                self.title =  splitfile[1].strip()
                self.album = splitfile[2].strip()
                return
            except:
                pass
        self.title = os.path.basename(name[:-4])
        self.artist = None
        self.album = None
        self.noid3 = False
        self.duration = None
        if useBuildin:
            size = os.stat(name).st_size
            f = open(name, 'rb')
            f.seek(size - 125)
            read = f.read(90)
            self.title = read[0:29].decode("utf-8").rstrip('\x00')
            self.artist = read[30:59].decode("utf-8").rstrip('\x00')
            self.album = read[60:89].decode("utf-8").rstrip('\x00')
        else:
            tfile = taglib.File(name)
            try:
                self.duration = tfile.length
                self.title = tfile.tags["TITLE"][0]
                self.artist = tfile.tags["ARTIST"][0]
                self.album = tfile.tags["ALBUM"][0]
            except KeyError:
                print("Could not find ID3 tags for %s" % name)
        if not self.title \
            or not self.artist \
            or not self.album:
            try:
                self.noid3 = True
                self.artist = splitfile[0].strip()
                self.title =  splitfile[1].strip()
                self.album = splitfile[2].strip()
            except:
                print("Could not infer tags for file %s" % name)



if __name__ == "__main__":
    f = ID3(sys.argv[1])
    print("%s %s %s" % (f.title, f.artist, f.album))