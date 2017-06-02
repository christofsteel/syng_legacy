import urllib.request
import urllib.parse
import json
import argparse

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
    queue_put_parser.add_argument("--singer", "-s")
    queue_put_parser.add_argument("--youtube", "-y", action="store_true")
    queue_put_parser.add_argument("songid")

    searchparser = subparsers.add_parser("search")
    searchparser.add_argument("query")

    args = parser.parse_args()
    endpoint = "http%s://%s:%s" % ("s" if args.https else "", args.host, args.port)
    if args.action == "queue":
        if args.queue == "get":
            print_queue(get_queue(endpoint))
        elif args.queue == "put":
            print_queue(put_queue(endpoint, args.songid, args.singer, 'youtube' if args.youtube else 'library'))
    if args.action == "search":
        print_results(search(endpoint, args.query))
