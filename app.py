#!venv/bin/python
from flask import Flask, jsonify, request, abort
import requests
from polyline import decode_line

app = Flask(__name__)

version = '/1.0'

# Google api prefs:
baseURL = 'http://maps.googleapis.com/maps/api'
format = '/json'

@app.route(version + '/geocode')
def geocode():
	q = request.args.get('q')
	params = {'address': q,
			   'sensor': "true"}
	r = requests.get(baseURL + '/geocode' + format, params=params)

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
	r = requests.get(baseURL + '/directions' + format, params=params)

	polyline = r.json()["routes"][0]["overview_polyline"]["points"]
	decoded = decode_line(polyline)
	ret = [{"lat": tup[0], "lng": tup[1]} for tup in decoded]
	return jsonify({"waypoints": ret})

if __name__ == '__main__':
    app.run(debug = True)
