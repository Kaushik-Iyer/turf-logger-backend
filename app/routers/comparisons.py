from fastapi import APIRouter, Depends
from starlette.requests import Request
from dotenv import load_dotenv
from datetime import datetime, timedelta
from .temp import fix_object_id, get_lat_long, maps_api_key
import requests
import pandas as pd
import os

def get_db(request: Request):
    db = request.app.state.client["TestDB"]
    return db

football_data_org_api_key = os.getenv('FOOTBALL_DATA_ORG_API_KEY')
router = APIRouter()

@router.get("/player_leaderboard/{period}")
async def get_player_leaderboard(period: str, db=Depends(get_db)):
    collection = db["players"]
    players = []
    now = datetime.now()

    if period == 'daily':
        start_date = now - timedelta(days=1)
    elif period == 'weekly':
        start_date = now - timedelta(weeks=1)
    elif period == 'monthly':
        start_date = now - timedelta(days=30)
    else:
        return "Invalid period. Please choose from 'daily', 'weekly', or 'monthly'."

    async for player in collection.find({"created_at": {"$gte": start_date}}):
        players.append(fix_object_id(player))
    
    df = pd.DataFrame(players)
    df['G/A'] = df['goals'] + df['assists']
    df = df.sort_values(by='G/A', ascending=False)

    return df.to_dict(orient='records')




# Maybe run a loop of this with different common areas of Mumbai, and save the results in a database to avoid 
#multiple API calls. 
#Future API calls will be made to the database instead of the Google Places API. If the data is not found in the database,
#then the API call will be made to the Google Places API.
@router.get("/turf_near_me")
async def get_turf_near_me(db=Depends(get_db)):
    lat, long = get_lat_long()

    base_url=f'https://places.googleapis.com/v1/places:searchText'
    params={
        'key':maps_api_key,
    }
    request_body={
        'textQuery':'football turf nearby',
        'locationBias': {
            'circle': {
                'center': {
                    'latitude': lat,
                    'longitude': long
                },
                'radius': 2500.0
            }
        },
        "maxResultCount":15
    }
    headers={
        'X-Goog-FieldMask':'places.displayName,places.location,places.googleMapsUri'
    }
    response=requests.post(base_url,params=params,json=request_body,headers=headers).json()
    #save the results in the database
    for turf in response['places']:
        latitude = turf['location']['latitude']
        longitude = turf['location']['longitude']
        turf['location'] = {
            'type': 'Point',
            'coordinates': [longitude, latitude]
        }
        db["turfs"].insert_one(turf)

    return response



@router.get("/players/{day}/{month}/{goals}/{assists}")
async def get_players(day: int, month: int, goals: int, assists: int):
    return {"Feature incomplete": "This feature is not yet implemented."}
    # df=pd.read_csv('backend/appearances.csv')
    # df['date'] = pd.to_datetime(df['date'])
    # df['month_day'] = df['date'].apply(lambda x: (x.month, x.day))
    # filtered_df = df[df['month_day'] == (month, day)]
    
    # # Filter players who have exactly the same number of goals and assists as specified
    # filtered_df = filtered_df[(filtered_df['goals'] == goals) & (filtered_df['assists'] == assists)]
    
    # # Get the first player and game_id
    # first_player = filtered_df.iloc[0]['player_name']
    # game_id = filtered_df.iloc[0]['game_id']

    # if pd.isnull(first_player) or pd.isnull(game_id):
    #     return {"player": "No player found", "home_team": "No team found", "away_team": "No team found"}

    # # Load the other CSV file
    # df2 = pd.read_csv('backend/games.csv')

    # # Find the row with the matching game_id
    # game_row = df2[df2['game_id'] == game_id].iloc[0]

    # # Get the home_team_name and away_team_name
    # home_team_name = game_row['home_club_name']
    # away_team_name = game_row['away_club_name']
    # date=game_row['date']


    # return {"player": first_player, "home_team": home_team_name, "away_team": away_team_name, "date": date}


#API to return live match scores
@router.get("/live_scores")
async def get_live_scores():
    uri = 'https://api.football-data.org/v4/matches'
    headers = { 'X-Auth-Token': football_data_org_api_key }

    response = requests.get(uri, headers=headers)
    matches=[]
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
    return matches
