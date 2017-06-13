import pafy
from . import app

def search(q):
    result = pafy.call_gdata('search', {
        'q': q,
        'maxResults': int(app.configuration["query"]["limit_results"]),
        'part': 'id,snippet',
        'type': 'video'
    })
    return [
        {
            'id': 'https://www.youtube.com/watch?v=%s' % item['id']['videoId'],
            'album': 'YouTube',
            'artist': item['snippet']['channelTitle'],
            'title': item['snippet']['title']
        } for item in result['items']]
