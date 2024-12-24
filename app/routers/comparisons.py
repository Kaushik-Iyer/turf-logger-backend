from fastapi import APIRouter, WebSocket
from starlette.requests import Request
from .temp import maps_api_key
import requests
import os
import asyncio

def get_db(request: Request):
    db = request.app.state.client["TestDB"]
    return db


football_data_org_api_key = os.getenv('FOOTBALL_DATA_ORG_API_KEY')
router = APIRouter()

from math import radians, sin, cos, sqrt, atan2

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return round(distance, 2)

@router.get("/turf_near_me")
async def get_turf_near_me(lat: float, long: float):
    base_url = f'https://places.googleapis.com/v1/places:searchText'
    params = {
        'key': maps_api_key,
    }
    request_body = {
        'textQuery': 'football turf nearby',
        'locationBias': {
            'circle': {
                'center': {
                    'latitude': lat,
                    'longitude': long
                },
                'radius': 2500.0
            }
        },
        "maxResultCount": 5
    }
    headers = {
        'X-Goog-FieldMask': 'places.displayName,places.location,places.googleMapsUri'
    }
    response = requests.post(base_url, params=params, json=request_body, headers=headers).json()
    
    # Add distance to each place
    for place in response.get('places', []):
        place['distance_km'] = calculate_distance(
            lat, 
            long,
            place['location']['latitude'],
            place['location']['longitude']
        )
    # Sort places by distance
    response['places'] = sorted(response.get('places', []), key=lambda x: x['distance_km'])
    
    return response

@router.websocket("/live_scores")
async def get_live_scores_websocket(websocket: WebSocket):
    await websocket.accept()
    while True:
        uri = 'https://api.football-data.org/v4/matches'
        headers = {'X-Auth-Token': football_data_org_api_key}
        response = requests.get(uri, headers=headers)
        matches = []
        for match in response.json()['matches']:
            match_info = {
                'time': match['utcDate'],
                'homeTeam': match['homeTeam']['name'],
                'awayTeam': match['awayTeam']['name'],
                'score': match['score']['fullTime'],
                'homeCrest': match['homeTeam']['crest'],
                'awayCrest': match['awayTeam']['crest']
            }
            matches.append(match_info)

        await websocket.send_json(matches)
        await asyncio.sleep(600)
