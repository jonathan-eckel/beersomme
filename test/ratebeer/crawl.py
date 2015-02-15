from bs4 import BeautifulSoup
import requests
from glob import glob
from HTMLParser import HTMLParser
import os
import numpy as np
import json

def getLinks(ss):

    files = glob("styles/" + ss)
    n = len(files)
    print files
    print n
    linkDict = {}
    for i,fn in enumerate(files):
        style = os.path.basename(fn).split('.')[-2] #get the fn without extension
        with open(fn) as f:
            soup = BeautifulSoup(f, ["lxml", "xml"])

        result = soup.findAll('A')
        result = result[1:] # remove first irrelevant link
        links = map(lambda x: x['HREF'], result)
        links = map(lambda x: x.encode('ascii'), links)
        linkDict[style] = links

    return linkDict


#print getLinks()[0][0]

#beerList = map(getLinks)


def extractDesc(link):
    r = requests.get("http://www.ratebeer.com" + link)
    html = r.text

    name = link.split('/')[2]

    div_block_ind = html.find('COMMERCIAL DESCRIPTION')
    if div_block_ind:
        substr = html[div_block_ind:]
        start = substr.find('</small>')
        substr = substr[start+len('</small>'):]
        end = substr.find('</div>')
        desc = substr[:end]
        desc = desc.replace('<br>', '')
    else:
        desc = ''

    parser = HTMLParser()

    desc = parser.unescape(desc)
    #desc = desc.encode('ascii')

    return {'beer': name, 'description': desc}

#name: desc}

#link = getLinks()[0][0]
linkDict = getLinks('*.html') #

#print linkDict['IPA']

for style, ell in linkDict.iteritems():

    #ell = linkDict['IPA']
    n = len(ell)

    output = [0]*n

    for i,myLink in enumerate(ell):
        print "http://www.ratebeer.com" + myLink    
        #extractDesc(myLink)
        #output[i] = extractDesc(myLink)

    #with open(style + '.json', 'w') as f:
        #json.dump(output, f)


