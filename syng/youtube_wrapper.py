import pafy

def search(q):
    result = pafy.call_gdata('search', {
        'q': q,
        'maxResults': 50,
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