from flask import render_template, request
from app import app
import pymysql as mdb

from geo import geo
from untappd import getPubFeed,getSQLBeerList,getSQLVenue,getLocalVenues

import numpy as np
import pandas as pd

db = mdb.connect(user="jeckel", passwd="data", 
        host="localhost", db="beerdb", charset='utf8')

similarity = np.load("similarity.npy")
df = pd.read_pickle("beerDataFrame.pkl")

@app.route('/db')
def cities_page():
    with db:
        cur = db.cursor()
        cur.execute("SELECT Name FROM City LIMIT 15;")
        query_results = cur.fetchall()
    cities = ""
    for result in query_results:
        cities += result[0]
        cities += "<br>"
    return cities

@app.route("/db_fancy")
def cities_page_fancy():
    with db:
        cur = db.cursor()
        cur.execute("SELECT Name, CountryCode, Population FROM City ORDER BY Population LIMIT 15;")

        query_results = cur.fetchall()
    cities = []
    for result in query_results:
        cities.append(dict(name=result[0], country=result[1], population=result[2]))
    return render_template('cities.html', cities=cities)

@app.route('/')
@app.route('/index')
@app.route('/input')
def beersomme_input():
    results = None
    with db:
        cur = db.cursor()
        sql = "SELECT id,name FROM ratebeer ORDER BY name"
        cur.execute(sql)
        results = cur.fetchall()
        print results
        return render_template("input.html", results=results)
    

@app.route('/output')
def beersomme_output():
    #pull 'ID' from input field and store it
    loc_address = request.args.get('userloc')
    #get GPS
    loc_gps = geo(loc_address)

    #pull 'ID' from selector and store it
    user_beer = request.args.get('userbeer')

    #get row of similarity matrix
    #from some model with pickled thing
    #down below

    #see whats nearby in my database
    venues = getLocalVenues(loc_gps, 1) #radius is optional second input

    print venues

    if len(venues) < 1:
        #call untappd
        checkins = getPubFeed(loc_gps)
        venues = [] #might be able to remove this
    
        for check in checkins:
            venue = check['venue']
            beer = check['beer']
            brewery = check['brewery']
    
            venueid = venue['venue_id']
            beerid = beer['bid']
    
            venues.append(venue)
    
    beerList = [] #{venueid: vid, beerList: []}

    for bar in venues:
        venueid = bar['venue_id']
        beers = getSQLBeerList(venueid)

        #add to db

        #if nbeers too small get more
        # CODE HERE
        if len(beers) > 0:
            beerList.append({'venueid': venueid, 'beerlist': beers})

    #match untappd beers to ratebeer beers
    #pick out the columns with the nearby beers
   
    listofbeerids = []
    listofnames = []
    listofvenues = []

    for ell in beerList:
        venueid = ell['venueid']
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
 

    if len(listofbeerids) < 1:
        # error page?
        # 1 -> no beers found!
        return render_template("input.html", error=1)

    #find best fit
    ind = df.index.get_loc(int(user_beer.encode('ASCII')))
    similar = similarity[ind, :] #old chub
    #for name, v in zip(listofnames, similar[listofbeerids]):
    #    print name, v
    
    similarsubset = similar[listofbeerids]
    rankingids = np.argsort(similarsubset)[::-1]
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
    return render_template("output.html", best_match = best_match, best_score = best_score, best_venue = best_venue)

