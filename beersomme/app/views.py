from flask import render_template, request
from app import app
import pymysql as mdb

from geo import geo
from untappd import getPubFeed, getSQLBeerList, getSQLVenue, getLocalVenues, updateDB, getMoreBeers

import numpy as np
import pandas as pd

db = mdb.connect(user="jeckel", passwd="data", 
        host="localhost", db="beerdb", charset='utf8')

similarity = np.load("data/similarity.npy", mmap_mode="r")
df = pd.read_pickle("data/beerDataFrame.pkl")

@app.route('/slides')
def slides():
    results = None
    return render_template("slides.html", results=results)

@app.route('/about')
def about():
    results = None
    return render_template("about.html", results=results)

@app.route('/')
@app.route('/input')
def beersomme_input():
    results = None
    with db:
        cur = db.cursor()
        sql = "SELECT id,name FROM ratebeer ORDER BY name"
        cur.execute(sql)
        results = cur.fetchall()
        #print results
        return render_template("input.html", results=results)
    

@app.route('/output')
def beersomme_output():
    #pull 'ID' from input field and store it
    loc_address = request.args.get('userloc')    

    #see if its a LAT LNG
    if loc_address.startswith("LAT:"):
        x = loc_address.split(",")
        lat = float(x[0].split(":")[1])
        lng = float(x[1].split(":")[1])
        loc_gps = {'lat': lat,'lng': lng}
    else:
        #get GPS
        loc_gps = geo(loc_address)

    radius = request.args.get('radius')


    #pull 'ID' from selector and store it
    user_beer = request.args.get('userbeer')

    #get row of similarity matrix
    #from some model with pickled thing
    #down below

    #see whats nearby in my database
    venues = getLocalVenues(loc_gps, radius) #radius is optional second input

    #print venues

    venueids = [v['venue_id'] for v in venues]

    if len(venues) < 10:
        #call untappd
        checkins = getPubFeed(loc_gps, radius=radius)
        #venues = [] #might be able to remove this
        
        nearbyVenues = updateDB(checkins)
    
        # TO FIX DUPLICATES and Add Proper location info
        for v in nearbyVenues:
            # Add Proper location info
            v.update(v['location'])
            if v['venue_id'] not in venueids:
                venues.append(v)
                venueids.append(v['venue_id'])

        #venues += [v if v['venue_id'] not in venueids for v in nearbyVenues]
        #venues += nearbyVenues

        """        
        for check in checkins:
            venue = check['venue']
            beer = check['beer']
            brewery = check['brewery']
    
            venueid = venue['venue_id']
            beerid = beer['bid']
    
            venues.append(venue)
        """

    beerList = [] #{venue: venue, beerList: []}
    #print venues


    for bar in venues:
        #print bar
        venueid = bar['venue_id']
        beers = getSQLBeerList(venueid)

        #add to db

        #if nbeers too small get more
        #number is relatively small to avoid excessive calls
        ncalls = 0        
        if ncalls < 5 and len(beers) < 3:
            getMoreBeers(venueid)
            ncalls += 1
            beers = getSQLBeerList(venueid)

        if len(beers) > 0:
            beerList.append({'venue': bar, 'beerlist': beers})

    #match untappd beers to ratebeer beers
    #pick out the columns with the nearby beers
   
    listofbeerids = []
    listofnames = []
    listofvenues = []

    matchedBeerList = [] #{venue: venue, beerList: []}

    for ell in beerList:
        venue = ell['venue']
        venueid = venue['venue_id']
        matchedBeers = []
        matchedids = []
        for beer in ell['beerlist']:
                beerName = beer['beer_name'].strip()
                if "Brewery" in beer['brewery_name']:
                    breweryName = beer['brewery_name'].split("Brewery")[0].strip()
                elif "Brewing" in beer['brewery_name']:
                    breweryName = beer['brewery_name'].split("Brewing")[0].strip()                
                elif "Beer" in beer['brewery_name']:
                    breweryName = beer['brewery_name'].split("Beer")[0].strip()
                else:
                    breweryName = beer['brewery_name'].strip()

                #remove accents
                breweryName = breweryName.replace("'", "")
                beerName = beerName.replace("'", "")

                if beerName.split()[0] == breweryName:
                    myName = breweryName + " " + beerName
                else:
                    myName = breweryName + " " + beerName
                #print myName
                #print df[df['name'].str.contains(myName)]
                x = df[df['name'] == myName]
                #print x
                if ( len(x) > 0 ):
                    ind = df.index.get_loc(x.index[0])
                    listofvenues.append(venueid)
                    listofnames.append(myName)
                    listofbeerids.append(ind)
                    matchedBeers.append(beer)
                    matchedids.append(ind)
        
        #print matchedBeers
        matchedBeerList.append({'venue': venue, 'beerList': matchedBeers, 'ids': matchedids})
 

    if len(listofbeerids) < 1:
        # error page?
        # 1 -> no beers found!
        #beersomme_input(error=1)
        return render_template("input.html", error=1)

    ind = df.index.get_loc(int(user_beer.encode('ASCII')))
    #get the Top n beers
    topBeerids = getTopBeers(listofbeerids, ind)
    #print topBeerids

    # get a score for each venue 
    topVenues = []
    keys = ['venue', 'score', 'beers']

    for d in matchedBeerList:
        venue = d['venue']
        myBeerList = d['beerList']
        myids = d['ids']
        #print venue, myBeerList, myids
        score, beers = getScore(myBeerList, myids, topBeerids, ind)
        #print score, venue['venue_name']
        if score > 0:
            topVenues.append(dict(zip(keys, [venue, score, beers])))

    #print topVenues
    # get info for the top 5 venues

    nVenues = 5

    outputVenues = [v['venue'] for v in sorted(topVenues, key=lambda x: x['score'], reverse=True)[:nVenues]]

    outputBeers = [b['beers'] for b in sorted(topVenues, key=lambda x: x['score'], reverse=True)[:nVenues]]

    outputScores = [v['score'] for v in sorted(topVenues, key=lambda x: x['score'], reverse=True)[:nVenues]]

    #print topVenues

    return render_template("output.html", topVenues = outputVenues, topBeers = outputBeers, topScores = outputScores)
    
    """
    #find best fit
    ind = df.index.get_loc(int(user_beer.encode('ASCII')))
    similar = similarity[ind, :] #old chub
    #for name, v in zip(listofnames, similar[listofbeerids]):
    #    print name, v
    
    similarsubset = similar[listofbeerids]
    rankingids = np.argsort(similarsubset)[::-1]

    # lets keep track of the top n (10)
    nBest = 10
    top_ids = rankingids[:10]
    arrayofnames = np.array(listofnames)
    arrayofvenues = np.array(listofvenues)
    top_names = arrayofnames[top_ids]
    top_scores = similarsubset[top_ids]
    top_venues = nBest*[0]    

    for i,vid in enumerate(arrayofvenues[top_ids]):
        top_venues[i] = getSQLVenue(int(vid))

    top_dict = [{"name": n,"score": s, "venue": v} for n,s,v in zip(top_names, top_scores, top_venues)]


    bestid = rankingids[0]

    best_match = listofnames[bestid]
    best_score = similarsubset[bestid]

    venueid = listofvenues[bestid]
    best_venue = getSQLVenue(venueid)

    #print best_venue
    print best_match.encode('ascii', 'ignore')
    print best_score


    #call a function from a_Model package. note we are only pulling one result in the query
    #pop_input = cities[0]['population']
    best_match = listofnames[bestid] #beerList
    #the_result = ModelIt(city, pop_input)
    return render_template("output.html", beerList = top_dict, best_match = best_match, best_score = best_score, best_venue = best_venue)
    """

def getScore(beerList, myids, topBeerids, beerInd):
    global similarity

    similar = similarity[beerInd, :]
    listofbeers = []
    listofbeerids = []

    #print topBeerids
    #print "len of beerlist", len(beerList)
    #print "len of myids", len(myids)
    #print myids

    # only take beers that are the 10 closest to mybeer
    for b,i in zip(beerList, myids):
        #print b, i
        if i in topBeerids:
            #print b, i
            listofbeers.append(b)
            listofbeerids.append(i)

    if len(listofbeers) < 1:
        return 0, []

    #print listofbeerids
    similarsubset = similar[listofbeerids]
    rankingids = np.argsort(similarsubset)[::-1]

    score = 0
    outputList = []
    for i in rankingids:
        #print "UM:", similarsubset[i]
        score += similarsubset[i]
        outputList.append(listofbeers[i])

    #print "SCORE:", score
    #print outputList
    return (score, outputList)

def getTopBeers(listofbeerids, beerInd):
    global similarity

    uniArray = np.unique(listofbeerids)

    similar = similarity[beerInd, :]
    similarsubset = similar[uniArray]
    rankingids = np.argsort(similarsubset)[::-1]

    # lets keep track of the top n (10)
    nBest = 10

    top_ids = uniArray[rankingids[:nBest]]

    return top_ids 

