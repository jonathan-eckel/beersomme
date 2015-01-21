import datetime
import requests
import json
import pymysql as mdb

ratelimit_MAX = 100
ratelimit_CURRENT = 0

apiurl = "https://api.untappd.com/v4"
clientId = "BB7A0B2F82AD836734DAB078A468EC41E87C8498"
clientSecret = "3AB6E7FBD8687B46ABE270B691C058A4C6F8F70B"

credentials = {'client_id':clientId, 'client_secret':clientSecret}

def addSQLVenue(venue):
    data_venue = {'venue_id': int(venue['venue_id']), 'venue_name': venue['venue_name'], 'primary_category': venue['primary_category'], 'foursquare_url': venue['foursquare']['foursquare_url']}
    data_venue.update(venue['location'])

    con = mdb.connect('localhost', 'jeckel', 'data', 'beerdb') #host, user, password, #database

    with con:
        cur = con.cursor()
        add_venue = "INSERT INTO venue(venueid,venue_name, category,fsq_url,address,state,city,lat,lng) VALUES(%(venue_id)s, %(venue_name)s, %(primary_category)s, %(foursquare_url)s, %(venue_address)s, %(venue_state)s, %(venue_city)s, %(lat)s, %(lng)s)"
        cur.execute(add_venue, data_venue)
        con.commit()
    
def addSQLBeer(beer,brewery):
    data_beer = {'bid': int(beer['bid']), 'beer_name': beer['beer_name'], 'brewery_name': brewery['brewery_name'], 'brewery_id': brewery['brewery_id'], 'brewery_slug': brewery['brewery_slug'], 'style': beer['beer_style'], 'abv': beer['beer_abv']}

    con = mdb.connect('localhost', 'jeckel', 'data', 'beerdb') #host, user, password, #database

    with con:
        cur = con.cursor()
        add_beer = "INSERT INTO beer(bid,beer_name, brewery_name,brewery_id,brewery_slug,style,abv) VALUES( %(bid)s,%(beer_name)s,%(brewery_name)s, %(brewery_id)s, %(brewery_slug)s, %(style)s,%(abv)s)"
        cur.execute(add_beer, data_beer)
        con.commit()

def addSQLBeerList(checkin):
    mytime =  checkin['created_at']
    mydate = datetime.datetime.strptime(mytime, "%a, %d %b %Y %X +0000")

    data_checkin = [checkin['venue']['venue_id'], checkin['beer']['bid'], mydate.strftime("%Y-%m-%d %X"), checkin['checkin_id']]

    con = mdb.connect('localhost', 'jeckel', 'data', 'beerdb') #host, user, password, #database

    with con:
        cur = con.cursor()
        add_checkin = "INSERT INTO beer_list(venueid,beerid, checkin_time, checkin_id) VALUES(%s, %s, %s, %s)"
        cur.execute(add_checkin, data_checkin)
        con.commit()


def getSQLBeer(beerid):

    con = mdb.connect('localhost', 'jeckel', 'data', 'beerdb') #host, user, password, #database

    beer = {}

    with con: 
        cur = con.cursor()
        cur.execute("SELECT * FROM beer WHERE bid=%s", beerid)
        rows = cur.fetchall()
        keys = ['id', 'bid','beer_name','brewery_name', 'brewery_id', 'brewery_slug', 'style','abv']
        beer = dict(zip(keys, rows))

    return beer

def getSQLVenue(venueid):

    con = mdb.connect('localhost', 'jeckel', 'data', 'beerdb') #host, user, password, #database

    venue = {}

    with con: 
        cur = con.cursor()
        cur.execute("SELECT * FROM venue WHERE venueid=%s", venueid)
        rows = cur.fetchall()
        keys = ['venue_id','venue_name','primary_category', 'foursquare_url','venue_address', 'venue_state', 'venue_city', 'lat', 'lng']
        venue = dict(zip(keys, rows))

    return venue

def getSQLBeerList(venueid, beerid):

    con = mdb.connect('localhost', 'jeckel', 'data', 'beerdb') #host, user, password, #database

    beerList = {}

    with con: 
        cur = con.cursor()
        cur.execute("SELECT beerid FROM beer_list WHERE venueid=%s AND beerid=%s", [venueid, beerid]) #change this to a join
        rows = cur.fetchall()
        if len(rows) > 0:
            keys = ['venue_id','beer_id','checkin_time', 'checkin_id'] 
            beerList = dict(zip(keys,rows))
        
    return beerList

    
def getPubFeed(lat, lng, **kwargs):
    global ratelimit_CURRENT

    pubfeed = "/thepub/local"
    payload = {'lat': lat, 'lng': lng}

    payload.update(kwargs)
    payload.update(credentials)
    
    r = requests.get(apiurl+pubfeed, params=payload)
    assert(r.status_code == requests.codes.ok)
    
    ratelimit_CURRENT = r.headers['x-ratelimit-remaining']

    return r.content


lat = '40.739627'
lng = '-73.988400'
#json_output = getPubFeed(lat, lng)
#output =  json.loads(json_output)

#with open("sample_pub.json", "w") as f:
#    json.dump(json_output,f)

with open("sample_pub.json", "r") as f:
    json_output = json.load(f)

output =  json.loads(json_output)

print ratelimit_CURRENT

resp = output['response']
checkins = resp['checkins']['items']
ncheckins = resp['checkins']['count']
for check in checkins:
    venue = check['venue']
    beer = check['beer']
    brewery = check['brewery']

    venueid = venue['venue_id']
    beerid = beer['bid']

    #see if beer is in the db
    sqlBeer = getSQLBeer(beerid)
    if len(sqlBeer) == 0: #not there, add it
        addSQLBeer(beer, brewery)

    #find venue
    sqlVenue = getSQLVenue(venueid)
    if len(sqlVenue) == 0: #not there, add it
        addSQLVenue(venue)

    #find beers
    beerList = getSQLBeerList(venueid, beerid)
    print beerList
    # see if checkin in beerlist:
    if len(beerList) == 0 or (check['checkin_id'] not in [b['checkin_id'] for b in beerList]):
        addSQLBeerList(check)

    


    #if len(beerList) < 5: # can change this number
    #    addSQLBeerList(check)
    #    beerList = getSQLBeerList(venueid, beerid)

