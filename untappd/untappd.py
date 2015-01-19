ratelimit_MAX = 100

apiurl = "https://api.untappd.com/v4"
clientId = "BB7A0B2F82AD836734DAB078A468EC41E87C8498"
clientSecret = "3AB6E7FBD8687B46ABE270B691C058A4C6F8F70B"

credentials = {'client_id':clientId, 'client_secret':clientSecret}


def getPubFeed(lat, lng, **kwargs):
    pubfeed = "/thepub/local"
    payload = {'lat': lat, 'lng': lng}

    payload.update(kwargs)
    payload.update(credentials)
    
    #r = requests.get(apiurl+pubfeed, params=payload)
    #assert(r.status_code == requests.codes.ok)
    
    #ratelimit_remaining = r.headers['x-ratelimit-remaining']
    #assert(ratelimit_remaining < ratelimit_MAX


    return payload

print getPubFeed(0, 0)
