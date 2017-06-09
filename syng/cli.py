import requests
import argparse

def skip(endpoint, password):
    result = requests.patch("%s/queue" % endpoint,
                            json={'action': 'skip'},
                            auth=('admin', password)
                            )
    return result.json()

def move_item(endpoint, password, source, dest):
    result = requests.patch("%s/queue" % endpoint,
                            json={'action': 'move', 'param': {'src': source, 'dst': dest}},
                            auth=('admin', password)
                            )
    return result.json()

def delete_item(endpoint, password, index):
    result = requests.patch("%s/queue" % endpoint,
                            json={'action': 'delete', 'param': {'index': index}},
                            auth=('admin', password)
                            )
    return result.json()

def put_queue(endpoint, song, singer=None, type="library"):
    result = requests.post("%s/queue" % endpoint, json={'singer': singer, 'id': song, 'type': type})
    return result.json()

def get_queue(endpoint):
    result = requests.get("%s/queue" % endpoint)
    return result.json()

def search(endpoint, query):
    result = requests.get("%s/query" % endpoint, params={'simple': True, 'q': query})
    return result.json()

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

def print_results(results):
    print("Result for query \"%s\":" % results['request']['q'])
    for row in results['result']:
        print("  %d:\t %s - %s [%s]" % (row['id'], row['artist'], row['title'], row['album']))

def main():
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
    skip_parser = queue_admin_subparser.add_parser("skip")
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
            if args.admin_action == "skip":
                print_queue(skip(endpoint, args.password))
            if args.admin_action == "delete":
                print_queue(delete_item(endpoint, args.password, args.index - 1))
            if args.admin_action == "move":
                print_queue(move_item(endpoint,args.password, args.source - 1, args.destination - 1))
    if args.action == "search":
        print_results(search(endpoint, args.query))

if __name__ == "__main__":
    main()