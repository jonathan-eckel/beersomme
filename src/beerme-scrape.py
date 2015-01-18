from bs4 import BeautifulSoup
import collections
import re
import requests
import numpy as np
import json

def extractBeer(beerBlock, brewery):

    divs = beerBlock.findAll('div')

    record = {}
    record['brewery'] = brewery

    beerName = divs[0].a.contents
    i = 1

    if divs[1].find('span', class_="OutOfDate"):
        record['style'] = 'Unknown'
    else:
        try:
            style = divs[1].a.contents
            record['style'] = style
            i += 1
        except AttributeError:
            print divs[1]
            pass

    record['name'] = beerName
    

    n = len(divs)

    d = collections.defaultdict(list)

    while i < n:
        currentDiv = divs[i]
        #print currentDiv
        if len(list(currentDiv.children)) == 1:
            abv = currentDiv.contents[0].split('%')[0]
            #print abv
            record['abv'] = abv
            i += 1
        elif 'class' in currentDiv.attrs:
            # d2 is award
            award = currentDiv
            i += 1
        else:
            # its a dateblock
            # find length of dateblock
        
            istart = i
            j = 1
            while i+j < n and 'Date' not in divs[i+j].text:
                j += 1
            istop = i+j
        
            dateBlock = divs[istart:istop]
            #if j == 5:
            #    d[u'Mouthfeel'].append([''])
            #    d[u'Appearance'].append([''])
            #    d[u'Aroma'].append([''])
            #    words = re.compile(r'[^A-Z^a-z]+').split(dateBlock[4].text)
            #    tag = words[0] + words[1]
            #    d[tag].append(words[2:])
            #else:
            for taste in dateBlock[4:]:
                    words = re.compile(r'[^A-Z^a-z]+').split(taste.text.replace('Overall Impression', 'OverallImpression'))
                    tag = words[0]
                    #d[tag].append(words[1:])
                    d[tag] += words[1:]
            
                #print dateBlock
                #words = re.compile(r'[^A-Z^a-z]+').split(dateBlock[7].text)
                #tag = words[0] + words[1]
                #d[tag].append(words[2:])
        
            i += j
        
    #record['description'] = d
    for k,v in d.iteritems():
        record[k] = v
    
    return record



#with open("beerme_bear_republic.html") as f:
#with open("beerme_avery.html") as f:
#    soup = BeautifulSoup(f)

nBrewery = 18678
beers = list()

#breweryId = 2911

# crashed at 16400

fns = [ "beerme_bear_republic.html" , "beerme_avery.html" , "crap.html" ]

try:

    for breweryId in range(16400, nBrewery+1):

        r = requests.get("http://beerme.com/brewery.php?" + str(breweryId))
        assert(r.status_code == requests.codes.ok)

        if breweryId % 100 == 0:
            print breweryId

        html = r.text

        #for fn in fns:
        #    assert(fn.endswith('html'))
        #with open(fn) as html:
        
        
        soup = BeautifulSoup(html)

        if not soup.find(class_='breweryName'):
            continue

        try:
            brewery = soup.find(class_='breweryName').contents[0]
        except AttributeError:
            continue
        except IndexError:
            continue

        for block in soup.findAll('li'): 
            if len(block.findAll('span', class_="OutOfDate")) > 0 and len(block.findAll('div', class_="beerName")) > 0:
                #print block
                beer = extractBeer(block, brewery)
                beers.append(beer)
        #print beers

except AssertionError:
    print breweryId    

finally:
    with open('beerme_beers16400' + '.json', 'w') as f:
        json.dump(beers, f)




