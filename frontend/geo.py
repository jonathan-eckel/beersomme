import geopy

def geo(address):
    geocoder = geopy.geocoders.GoogleV3()
    loc = geocoder.geocode(address)
    return {"lat": loc.latitude, "lng": loc.longitude}


