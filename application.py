#!venv/bin/python
import requests
import ConfigParser
from datetime import datetime
from flask import Flask, jsonify, request, abort
from polyline import decode_line
from requests_futures.sessions import FuturesSession


app = Flask(__name__)

version = '/1.0'

secrets = ConfigParser.ConfigParser()
secrets.read("secrets.cfg")

# Google api prefs:
googBaseURL = 'https://maps.googleapis.com/maps/api'
format = '/json'

# Foursquare:
fsBaseURL = 'https://api.foursquare.com/v2'

@app.route('/')
def index():
	return "Byway"

@app.route(version + '/geocode')
def geocode():
	q = request.args.get('q')
	params = {'address': q,
			   'sensor': "true"}
	r = requests.get(googBaseURL + '/geocode' + format, params=params)

	if r.json()["status"] == "OVER_QUERY_LIMIT":
		abort(429)

	result = r.json()["results"][0]
	coords = result["geometry"]["location"]
	address = result["formatted_address"]
	return jsonify({"coords": coords, "address": address})


@app.route(version + '/route')
def directions():
	waypoints = request.args.get('waypoints').split('|')
	params = {"origin": waypoints[0],
		 "destination": waypoints[-1],
		 	  "sensor": "true"}
	if len(waypoints) > 2:
		params["waypoints"] = "optimize:true|" + "|".join(waypoints[1:-1])
	r = requests.get(googBaseURL + '/directions' + format, params=params)

	polyline = r.json()["routes"][0]["overview_polyline"]["points"]
	decoded = decode_line(polyline)
	formatted = [{"lat": tup[0], "lng": tup[1]} for tup in decoded]
	return jsonify({"polyline": formatted, "encoded": polyline})


@app.route(version + '/venues')
def venues():
	category = request.args.get('category')
	encoded = request.args.get('polyline')
	decoded = decode_line(encoded)

	clientID = secrets.get("foursquare", "clientID")
	clientSecret = secrets.get("foursquare", "clientSecret")

	session = FuturesSession()
	reqs = []
	for waypt in decoded[0::20]:
		reqs.append(getVenuesNearLocation(waypt, category, clientID, clientSecret, session))
	
	allVenues = []
	ids = []   #<- for uniquing 
	for req in reqs:
		response = req.result()
		json = response.json()
		venues = [item["venue"] for item in json["response"]["groups"][0]["items"]
					if item["venue"]["id"] not in ids]
		ids.extend([venue["id"] for venue in venues])
		allVenues.extend(venues)
	return jsonify({"venues": allVenues})

def getVenuesNearLocation(coords, category, clientID, clientSecret, session):
	ll = str(coords[0]) + ',' + str(coords[1])
	date = datetime.now().strftime("%Y%m%d")
	params = {"ll": ll,
		 "section": category,
       "client_id": clientID,
   "client_secret": clientSecret,
			   "v": date,
		   "limit": 5}
	return session.get(fsBaseURL + "/venues/explore", params=params)

if __name__ == '__main__':
    app.run(debug = True)
