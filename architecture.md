Syng v2
=======

Overview
--------

Syng is a karaoke playback software with modularity, extensionality and high configurability in mind. It can be used to host karaoke events, using hold a queue to determin the next performer. Atendees can use their own devices to search available songs and add themselves to the queue via a web frontend. Syng by itself handles the queue and invokes external player to play the requested song.

Components
----------

Syng consists of the following components:

  * Queue
  * Webserver
  * Client
  * Index
  * Sources

Webserver
---------

The webserver listens for connections and manages the queue. It serves the main and admin html interface. In addition it offeres the following endpoints:

 - GET /queue
   This returns the currently played song, the queue and the last ten played songs in a json object. The currently played song is  The entries of the the current queue as list of entries in a json format.
   The entries have the following format:

   ```
   {
    'artist': 'ARTIST OF THE SONG',
    'title': 'TITLE OF THE SONG',
    'album': 'ALBUM OF THE SONG',
    'performer': 'PERFORMER OF THE SONG',
    'duration': 'DURATION OF THE SONG IN SECONDS'
   }
   ```

 - POST /queue
   This appends a song to the queue.
   The data is a json object with the following format:

   ```
   {
     'id': 'THE INTERNAL ID OF THE SONG',
     'source': 'THE NAME OF THE SOURCE',
     'performe': 'THE PERFORMER OF THE SONG'
   }
   ```

  
