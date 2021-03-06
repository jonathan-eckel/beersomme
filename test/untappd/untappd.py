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
        cur.execute("SELECT DISTINCT venue.venueid, beerid FROM checkin JOIN venue ON checkin.venueid=venue.venueid WHERE venue.venueid=%s", venueid)
        rows = cur.fetchall()
        beerList = rows
        
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
            nearbyVenues.append(venueid)

    return nearbyVenues
    

    
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

def getVenueFeed(venueid, **kwargs):
    global ratelimit_CURRENT

    venuefeed = "/venue/checkins/" + str(venueid)
    payload = {}

    payload.update(kwargs)
    payload.update(credentials)
    
    r = requests.get(apiurl+venuefeed, params=payload)
    assert(r.status_code == requests.codes.ok)

    ratelimit_CURRENT = r.headers['x-ratelimit-remaining']

    return r.content

def fixEncoding(name):
    utf_name = name.encode("UTF-8")
    #print utf_name
    ascii_name = unicode(utf_name, errors='ignore')
    #print ascii_name
    ascii_name = ascii_name.replace("()","")
    return ascii_name.strip()

lat = '40.739627'
lng = '-73.988400'
json_output = getPubFeed(lat, lng, radius=1)
output =  json.loads(json_output)

#with open("sample_pub.json", "w") as f:
#    json.dump(json_output,f)

#with open("sample_pub.json", "r") as f:
#    json_output = json.load(f)

#output =  json.loads(json_output)

print ratelimit_CURRENT

resp = output['response']
checkins = resp['checkins']['items']
ncheckins = resp['checkins']['count']

nearbyVenues = updateDB(checkins)

"""
nearbyVenues = []

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

    #see if checkin is in the db
    sqlCheckin = getSQLCheckin(check['checkin_id'])
    if len(sqlCheckin) == 0: #not there, add it
        addSQLCheckin(check)

    #keep track of nearby venues
    nearbyVenues.append(venueid)
"""

#now create beerLists, make a maximum of 5 calls
ncalls = 0
beerList = []
for venueid in nearbyVenues:
    sqlBeerList = getSQLBeerList(venueid)

    if (ncalls < 50) and (len(sqlBeerList) < 50):    
        #find more beers
        print "GETTING VENUE"
        jsonoutput = getVenueFeed(venueid)
        ncalls += 1
        output = json.loads(jsonoutput)

        resp = output['response']
        checkins = resp['checkins']['items']
        ncheckins = resp['checkins']['count']
        updateDB(checkins)
        
        #query again
        sqlBeerList = getSQLBeerList(venueid)

    beerList.append({'venueid': venueid, 'beers': sqlBeerList})
 

#print beerList

