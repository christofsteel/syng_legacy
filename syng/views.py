from flask import jsonify, request, render_template
from sqlalchemy import and_

from . import app, auth, appname_pretty, version, db
from .database import Songs, Artists
from .youtube_wrapper import search, yt_cache
from .synctools import Entry

@app.route('/comments', methods=['GET'])
def get_comments():
    song = request.args.get("song")
    with app.rwlock.locked_for_read():
        comments = Comments.query.filter(Comments.song_id == song).all()
    return jsonify(result = [{'name': comment.name, 'comment': comment.comment} for comment in comments])

@app.route('/comments', methods=['POST'])
def post_comment():
    json = request.get_json(force=True)


@app.route('/query', methods=['GET'])
def query():
    try:
        args = request.args
        qtype = args.get("type")
        query = args.get("q")
        res = []
        if qtype == "library":
            with app.rwlock.locked_for_read():
                #title = Songs.query.filter(Songs.title.like("%%%s%%" % query)).limit(int(app.configuration["query"]["limit_results"])).all()
                if db.dbtype == "postgres":
                    title = Songs.query.search(query).order_by(Songs.id).limit(int(app.configuration["query"]["limit_results"])).all()
                else:
                    filter_rules = [Songs.filename.like("%%%s%%" % subq) for subq in query.split(" ")]
                    title = Songs.query.filter(and_(*filter_rules)).order_by(Songs.id).limit(int(app.configuration["query"]["limit_results"])).all()
                res = [r.to_dict() for r in set(title)]
        elif qtype == "youtube":
            channel = args.get("yt-channel") #Work in progress
            if channel == "no_channel":
                # print(query)
                res = search(query, None)
            else:
                res = search(query, channel)
    except:
        res = []
    return jsonify(result = res, request=request.args)

@app.route('/queue', methods=['GET'])
def get_queue():
    queue = app.queue.get_list()
    return jsonify(current = app.current, queue = queue, last10 = app.last10)

def add_to_queue(item):
    content = Entry.from_dict(item)
    if app.caching \
            and content['type'] == 'youtube':
        content = yt_cache(content)
    app.queue.put(content)

@app.route('/queue', methods=['POST'])
def append_queue():
    json = request.get_json(force=True)
    if type(json) == list:
        print("Hey, list")
        for item in json:
            add_to_queue(item)
    else:
        add_to_queue(json)
    queue = app.queue.get_list()
    return jsonify(current = app.current, queue = queue, last10 = app.last10)

@app.route('/queue', methods=['PATCH'])
@auth.required
def alter_queue():
    json = request.get_json(force=True)
    action = json["action"]
    if action == "kill":
        app.process.kill()
    if action == "skip":
        app.process.terminate()
    if action == "delete":
        index = json["param"]["index"]
        app.queue.delete(index)
    elif action == "move":
        src = json["param"]["src"]
        dst = json["param"]["dst"]
        app.queue.move(src, dst)
    queue = app.queue.get_list()
    return jsonify(current = app.current, queue = queue, last10 = app.last10)

@app.route('/admin', methods=['GET'])
@auth.required
def admin_index():
    return render_template("index.html", admin=True, appname=appname_pretty, version=version, channels=app.channels, only_channels=app.only_channels, no_channels=app.no_channels)

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html", appname=appname_pretty, version=version, channels=app.channels, only_channels=app.only_channels, no_channels=app.no_channels)
