#!/usr/bin/env python

import json
import gzip
import numpy as np
import pandas as pd

## NLP Stuff
import scipy
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
import re

# similarity metric
from sklearn.metrics.pairwise import cosine_similarity

#database stuff
import pymysql as mdb

# load files
with gzip.open("data/allbeerdata.json.gz", "r") as f:
    data = json.load(f)
with gzip.open("data/topbeers.json.gz", "r") as f:
    datatop = json.load(f)

#massage into pandas dataframe
results = data['results']
results.keys()

topresults = datatop['results']

beerData = results['beer']
beerData += topresults['beer'] #append to list

#function to arrange dictionary for dataframe format
def mappy(beer):
    x = {}
    x['Style'] = beer['style']['text']
    brewery = beer['brewery']['text']
    if "Brewed by" in brewery:
        brewery = brewery.split("Brewed by")[1]
    elif "Formerly brewed at" in brewery:
        brewery = brewery.split("Formerly brewed at")[1]
    elif "Brewed at" in brewery:
        brewery = brewery.split("Brewed at")[0]

    x['Brewery'] = brewery
    beer.update(x)
    del beer['brewery']
    del beer['style']

map(mappy, beerData)

#ignore beerinfo for now

#raw dataframe
df_raw = pd.DataFrame(beerData)

# remove short description beers, remove duplicates
a = df_raw[df_raw['description'].notnull()]
df = a[a['description'] != '']
df = df[df.description.str.len() > 40]
df = df.drop_duplicates()

#sort df by style for debugging purposes
df = df.sort(columns='Style')

#total corpus of descriptions
corpus = df['description']

#remove bad entries
remove_list = []

for cor,i in zip(corpus, corpus.index):
    if type(cor) != unicode:
        #print i,cor
        remove_list.append(i)

df = df.drop( remove_list)
corpus = corpus.drop( remove_list)

# function to deal with unicode, as well as remove "newlines"
def myDecode(myStr):
    a = unicode(myStr).encode("UTF-8")
    a = a.decode("ASCII", errors="ignore")
    return a.replace('\n', " ")

# run vectorizer once to remove words that don't match
mycorpus = map(myDecode, corpus.values)
s = set(stopwords.words('english'))
vectorizer = CountVectorizer(max_df=1)
X = vectorizer.fit_transform(mycorpus)
nomatchwords = vectorizer.get_feature_names()
s = s.union(nomatchwords)
#print s

vectorizer = CountVectorizer(stop_words=s)
X = vectorizer.fit_transform(mycorpus)
keywords = vectorizer.get_feature_names()

#remove words that start with a number
prog = re.compile(r"[0-9]")
for key in keywords:
    if prog.match(key):
        s.add(key)

# final vectorizer using tfidf weighting
vectorizer = TfidfVectorizer(stop_words=s)
X = vectorizer.fit_transform(mycorpus)

keywords = vectorizer.get_feature_names()
counts = X.sum(axis=0)
counts = np.array(counts.T).squeeze()
wc = zip(keywords,counts)

#no stemming for now

#compute cosine similarity matrix
cs = cosine_similarity(X)
# save it as .npy file
np.save("frontend/data/similarity",cs)

print "Size of similarity matrix"
print cs.shape
print "Number of items"
print len(corpus)

#save pandas df to pickle
df.to_pickle("frontend/data/beerDataFrame.pkl")

#update mysql database
db = mdb.connect(user="jeckel", passwd="data", host="localhost", db="beerdb", charset='utf8')

with db:
   cur = db.cursor()
   cur.execute("DROP TABLE IF EXISTS ratebeer")
   cur.execute("CREATE TABLE ratebeer(id INT PRIMARY KEY,name VARCHAR(80))")
   for i,n in zip(df.index, df.name):
       cur.execute("INSERT INTO ratebeer(id, name) VALUES(%s, %s)", [str(i),n])
   db.commit()


