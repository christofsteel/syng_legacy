from flask import jsonify, request, render_template

from . import app, auth, appname_pretty, version
from .database import Songs, Artists
from .youtube_wrapper import search
from .main import Entry

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
    args = request.args
    qtype = args.get("type")
    query = args.get("q")
    res = []
    if qtype == "library":
        with app.rwlock.locked_for_read():
            #title = Songs.query.filter(Songs.title.like("%%%s%%" % query)).limit(int(app.configuration["query"]["limit_results"])).all()
            title = Songs.query.search(query).limit(int(app.configuration["query"]["limit_results"])).all()
            print(title)
            res = [r.to_dict() for r in set(title)]
    elif qtype == "youtube":
        channel = args.get("channel")
        if channel == None:
            print(query)
            res = search(query)


    return jsonify(result = res, request=request.args)

@app.route('/queue', methods=['GET'])
def get_queue():
    queue = app.queue.get_list()
    return jsonify(current = app.current, queue = queue, last10 = app.last10)

@app.route('/queue', methods=['POST'])
def append_queue():
    json = request.get_json(force=True)
    content = Entry.from_dict(json)
    app.queue.put(content)
    queue = app.queue.get_list()
    return jsonify(current = app.current, queue = queue, last10 = app.last10)

@app.route('/queue', methods=['PATCH'])
@auth.required
def alter_queue():
    json = request.get_json(force=True)
    action = json["action"]
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
    return render_template("index.html", admin=True, appname=appname_pretty, version=version)

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html", appname=appname_pretty, version=version)
