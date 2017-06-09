Syng
====

![Syng](https://opensomething.org/syng/syng.png)

Syng is a webbased karaoke client written in Python. It manages a
playlist and forwards the top element of playlist to a configurable
media player. Songs can be played from a library or from youtube. Once
the software is started, it listens for a HTTP connection (Default on
Port 1337) for control. Clients can connect via a web interface and
search and add songs, which are played on the server.

Installation
------------

Install with:

    pip install git+https://git.k-fortytwo.de/christofsteel/syng

It needs at least Python34.

First run
---------

Launch it with:

    syng

At first launch, syng will create a configuration file at
`${HOME}/.config/syng/syng.config`. Syng will look for cdg and mkv files
in the folder `${HOME}/.local/share/syng/songs`. If you need to have
your files in a different location, you can exit the software and edit
the configuration file. Launch it again with the option `--scan` to
start scanning for new files.

Syng will now start a webserver on <http://localhost:1337>

Administration
--------------

You can set a password for an admin user in the configuration file. The
admin interface is reachable under <http://localhost:1337/admin> .
Username is `admin` and the default password is also `admin`. In the
admin interface you can modify the playlist and skip songs.

Command line interface
----------------------

There is also a command line interface, mainly for testing purposes. See
`syng_cli --help` for help.
