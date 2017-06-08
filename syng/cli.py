import urllib.request
import urllib.parse
import json
import argparse

def move_item(endpoint, password, source, dest):
    passwd_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passwd_mgr.add_password(None, endpoint, 'admin', password)
    auth_handler = urllib.request.HTTPBasicAuthHandler(passwd_mgr)
    opener = urllib.request.build_opener(auth_handler)
    urllib.request.install_opener(opener)
    request = urllib.request.Request("%s/queue" % endpoint, method="UPDATE",
                                     data=json.dumps({'action': 'move', 'param': {'src': source, 'dst': dest}} ).encode())
    result = urllib.request.urlopen(request)
    return json.load(result)

def delete_item(endpoint, password, index):
    passwd_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passwd_mgr.add_password(None, endpoint, 'admin', password)
    auth_handler = urllib.request.HTTPBasicAuthHandler(passwd_mgr)
    opener = urllib.request.build_opener(auth_handler)
    urllib.request.install_opener(opener)
    request = urllib.request.Request("%s/queue" % endpoint, method="UPDATE",
                                     data=json.dumps({'action': 'delete', 'param': {'index': index}} ).encode())
    result = urllib.request.urlopen(request)
    return json.load(result)

def put_queue(endpoint, song, singer=None, type="library"):
    result = urllib.request.urlopen("%s/queue" % endpoint,
                                    data=json.dumps({'singer': singer, 'id': song, 'type': type}).encode())
    return json.load(result)

def get_queue(endpoint):
    result = urllib.request.urlopen("%s/queue" % endpoint)
    return json.load(result)

def print_queue(queue):
    if(queue['current'] != None):
        song = queue['current']
        print("Now Playing: %s - %s [%s] : %s" % (song['artist'], song['title'], song['album'], song['singer']))
    else:
        print("Not Playing")
    print("\nQueue:")
    for i, song in enumerate(queue['queue']):
        print("\t%d. %s - %s [%s] : %s" % (i+1, song['artist'], song['title'], song['album'], song['singer']))
    print("\nRecent:")
    for i, song in enumerate(queue['last10']):
        print("\t%d. %s - %s [%s] : %s" % (i+1, song['artist'], song['title'], song['album'], song['singer']))

def search(endpoint, query):
    result = urllib.request.urlopen("%s/query?%s" % (endpoint, urllib.parse.urlencode({'simple': True, 'q': query})))
    return json.load(result)

def print_results(results):
    print("Result for query \"%s\":" % results['request']['q'])
    for row in results['result']:
        print("  %d:\t %s - %s [%s]" % (row['id'], row['artist'], row['title'], row['album']))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", "-H", default="localhost")
    parser.add_argument("--port", "-p", default="1337")
    parser.add_argument("--https", action='store_true')

    subparsers = parser.add_subparsers(dest = "action")

    queue_parser = subparsers.add_parser("queue")
    queue_subparsers = queue_parser.add_subparsers(dest = 'queue')
    queue_get_parser = queue_subparsers.add_parser("get")
    queue_put_parser = queue_subparsers.add_parser("put")
    queue_admin_parser = queue_subparsers.add_parser("admin")
    queue_put_parser.add_argument("--singer", "-s")
    queue_put_parser.add_argument("--youtube", "-y", action="store_true")
    queue_put_parser.add_argument("songid")
    queue_admin_parser.add_argument("--password", "-pw", required=True)
    queue_admin_subparser = queue_admin_parser.add_subparsers(dest = "admin_action")
    delete_parser = queue_admin_subparser.add_parser("delete")
    delete_parser.add_argument("index", type=int)
    move_parser = queue_admin_subparser.add_parser("move")
    move_parser.add_argument("source", type=int)
    move_parser.add_argument("destination", type=int)


    searchparser = subparsers.add_parser("search")
    searchparser.add_argument("query")

    args = parser.parse_args()
    endpoint = "http%s://%s:%s" % ("s" if args.https else "", args.host, args.port)
    if args.action == "queue":
        if args.queue == "get":
            print_queue(get_queue(endpoint))
        elif args.queue == "put":
            print_queue(put_queue(endpoint, args.songid, args.singer, 'youtube' if args.youtube else 'library'))
        elif args.queue == "admin":
            if args.admin_action == "delete":
                print_queue(delete_item(endpoint, args.password, args.index - 1))
            if args.admin_action == "move":
                print_queue(move_item(endpoint,args.password, args.source - 1, args.destination - 1))
    if args.action == "search":
        print_results(search(endpoint, args.query))
