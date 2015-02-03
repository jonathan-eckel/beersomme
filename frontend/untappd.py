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

con = mdb.connect('localhost', 'jeckel', 'data', 'beerdb', charset='utf8') #host, user, password, #database

def addSQLVenue(venue):
    data_venue = {'venue_id': int(venue['venue_id']), 'venue_name': venue['venue_name'], 'primary_category': venue['primary_category'], 'foursquare_url': venue['foursquare']['foursquare_url']}
    data_venue.update(venue['location'])

    with con:
        cur = con.cursor()
        add_venue = "INSERT INTO venue(venueid,venue_name, category,fsq_url,address,state,city,lat,lng) VALUES(%(venue_id)s, %(venue_name)s, %(primary_category)s, %(foursquare_url)s, %(venue_address)s, %(venue_state)s, %(venue_city)s, %(lat)s, %(lng)s)"
        cur.execute(add_venue, data_venue)
        con.commit()
    
def addSQLBeer(beer,brewery):
    data_beer = {'bid': int(beer['bid']), 'beer_name': beer['beer_name'], 'brewery_name': brewery['brewery_name'], 'brewery_id': brewery['brewery_id'], 'brewery_slug': brewery['brewery_slug'], 'style': beer['beer_style'], 'abv': beer['beer_abv']}

    with con:
        cur = con.cursor()
        add_beer = "INSERT INTO beer(bid,beer_name, brewery_name,brewery_id,brewery_slug,style,abv) VALUES( %(bid)s,%(beer_name)s,%(brewery_name)s, %(brewery_id)s, %(brewery_slug)s, %(style)s,%(abv)s)"
        cur.execute(add_beer, data_beer)
        con.commit()

def addSQLCheckin(checkin):
    mytime =  checkin['created_at']
    mydate = datetime.datetime.strptime(mytime, "%a, %d %b %Y %X +0000")

    data_checkin = [checkin['venue']['venue_id'], checkin['beer']['bid'], mydate.strftime("%Y-%m-%d %X"), checkin['checkin_id']]

    with con:
        cur = con.cursor()
        add_checkin = "INSERT INTO checkin(venueid,beerid, checkin_time, checkin_id) VALUES(%s, %s, %s, %s)"
        cur.execute(add_checkin, data_checkin)
        con.commit()


def getSQLBeer(beerid):

    beer = {}

    with con: 
        cur = con.cursor()
        nonNull = cur.execute("SELECT * FROM beer WHERE bid=%s", beerid)
        row = cur.fetchone()
        if nonNull:
            keys = ['id', 'bid','beer_name','brewery_name', 'brewery_id', 'brewery_slug', 'style','abv']
            beer = dict(zip(keys, row))

    return beer

def getSQLVenue(venueid):

    venue = {}

    with con: 
        cur = con.cursor()
        nonNull = cur.execute("SELECT * FROM venue WHERE venueid=%s", venueid)
        row = cur.fetchone()
        if nonNull:    
            keys = ['venue_id','venue_name','primary_category', 'foursquare_url','venue_address', 'venue_state', 'venue_city', 'lat', 'lng']
            venue = dict(zip(keys, row))

    return venue

def getSQLCheckin(checkin_id):

    checkin = {}

    with con: 
        cur = con.cursor()
        nonNull = cur.execute("SELECT * FROM checkin WHERE checkin_id=%s", checkin_id)
        row = cur.fetchone()
        if nonNull:
            keys = ['venue_id','beer_id','checkin_time', 'checkin_id'] 
            checkin = dict(zip(keys,row))
        
    return checkin


def getSQLBeerList(venueid):

    beerList = []

    with con: 
        cur = con.cursor()
        #nonNull = cur.execute("SELECT DISTINCT beerid FROM checkin JOIN venue ON checkin.venueid=venue.venueid WHERE venue.venueid=%s", venueid)
        nonNull = cur.execute("SELECT beer.beer_name, beer.brewery_name, beer.style FROM beer WHERE beer.bid IN (SELECT DISTINCT checkin.beerid FROM checkin JOIN venue ON checkin.venueid=venue.venueid WHERE venue.venueid=%s)", venueid)
        rows = cur.fetchall()
        if nonNull:
            for row in rows:        
                beerList.append({'beer_name': row[0], 'brewery_name': row[1], 'style': row[2]})
        
    return beerList


def updateDB(checkins):
    nearbyVenues = []

    for check in checkins:
        venue = check['venue']
        beer = check['beer']
        brewery = check['brewery']

        beerid = beer['bid']

        #fix formatting
        beer['beer_name'] = fixEncoding(beer['beer_name'])
        brewery['brewery_name'] = fixEncoding(brewery['brewery_name'])

        #see if beer is in the db
        sqlBeer = getSQLBeer(beerid)
        if len(sqlBeer) == 0: #not there, add it
            addSQLBeer(beer, brewery)


        if len(venue) > 0:
            venueid = venue['venue_id']
            venue['venue_name'] = fixEncoding(venue['venue_name'])

            #find venue
            sqlVenue = getSQLVenue(venueid)
            if len(sqlVenue) == 0: #not there, add it
                addSQLVenue(venue)

            #see if checkin is in the db
            sqlCheckin = getSQLCheckin(check['checkin_id'])
            if len(sqlCheckin) == 0: #not there, add it
                addSQLCheckin(check)

            #keep track of nearby venues
            nearbyVenues.append(venue)

    return nearbyVenues
    
def getMoreBeers(venueid):
    #global ncalls
    checkins = getVenueFeed(venueid)
    #ncalls += 1
    updateDB(checkins)
    return

    
def getPubFeed(loc, **kwargs):
    """
    max_id (int, optional) - The checkin ID that you want the results to start with
    min_id (int, optional) - Returns only checkins that are newer than this value
    limit (int, optional) - The number of results to return, max of 25, default is 25
    radius (int, optional) - The max radius you would like the check-ins to start within, max of 25, default is 25
    dist_pref (string, optional) - If you want the results returned in miles or km. Available options: "m", or "km". Default is "m"
    """

    global ratelimit_CURRENT

    pubfeed = "/thepub/local"
    payload = loc

    payload.update(kwargs)
    payload.update(credentials)
    
    r = requests.get(apiurl+pubfeed, params=payload)
    assert(r.status_code == requests.codes.ok)
    
    ratelimit_CURRENT = r.headers['x-ratelimit-remaining']
    #return r.content
    output = json.loads(r.content)

    resp = output['response']
    checkins = resp['checkins']['items']
    ncheckins = resp['checkins']['count']

    #add distance
    for check in checkins:
        venue = check['venue']
        venue['dist'] = gpsDistance(loc, {'lat': venue['location']['lat'], 'lng': venue['location']['lng']})

    return checkins

def getVenueFeed(venueid, **kwargs):
    global ratelimit_CURRENT

    venuefeed = "/venue/checkins/" + str(venueid)
    payload = {}

    payload.update(kwargs)
    payload.update(credentials)
    
    r = requests.get(apiurl+venuefeed, params=payload)
    assert(r.status_code == requests.codes.ok)

    ratelimit_CURRENT = r.headers['x-ratelimit-remaining']
    output = json.loads(r.content)

    resp = output['response']
    checkins = resp['checkins']['items']
    ncheckins = resp['checkins']['count']

    return checkins
    #return r.content

def gpsDistance(loc1, loc2):
    from math import acos, sin, cos, radians

    lat1 = loc1['lat']
    lng1 = loc1['lng']
    lat2 = loc2['lat']
    lng2 = loc2['lng']
    
    # distance in miles
    dist = 3959.0 * acos( cos( radians(lat2) ) * cos( radians(lat1) ) * cos( radians(lng2) - radians(lng1) ) + sin( radians(lat2) ) * sin( radians(lat1) ) )

    return dist


def fixEncoding(name):
    utf_name = name.encode("UTF-8")
    #print utf_name
    ascii_name = unicode(utf_name, errors='ignore')
    #print ascii_name
    ascii_name = ascii_name.replace("()","")
    return ascii_name.strip()

def getLocalVenues(loc_gps, radius=1):
    nearbyVenues = []
    keys = ['venue_id','venue_name','primary_category', 'foursquare_url','venue_address', 'venue_state', 'venue_city', 'lat', 'lng', 'dist']

    data_local = {"radius": radius}
    data_local.update(loc_gps)

    with con:
        cur = con.cursor() 
        find_local = "SELECT * , (3959 * acos( cos( radians( %(lat)s ) ) * cos( radians( lat ) ) * cos( radians( %(lng)s ) - radians(lng) ) + sin( radians( %(lat)s ) ) * sin( radians(lat) ) )) AS distanta FROM venue WHERE lat<>'' AND lng<>'' AND (category='Food' OR category='Nightlife Spot') HAVING distanta<%(radius)s  ORDER BY distanta ASC"
        cur.execute(find_local, data_local)
        rows = cur.fetchall()
        for row in rows:
            venue = dict(zip(keys, row))
            nearbyVenues.append(venue)

    return nearbyVenues #dist included as key


