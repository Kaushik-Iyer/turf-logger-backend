from fastapi import APIRouter, Depends
from .temp import fix_object_id, Player, verify_jwt
from datetime import datetime, timedelta
from fastapi.responses import HTMLResponse
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, DateFormatter
import io
import base64
import urllib.parse
from starlette.requests import Request

def get_db(request: Request):
    db = request.app.state.client["TestDB"]
    return db

router = APIRouter()

@router.post("/entries")
async def create_player(player: Player, db=Depends(get_db),user=Depends(verify_jwt)):
    collection = db["entries"]
    player_data = player.model_dump()
    player_data["created_at"] = datetime.now()
    player_data["email"] = user['email']
    # Find existing record with the same email and created_at date
    existing_record = await collection.find_one({
        "email": user['email'],
        "created_at": {
            "$gte": datetime(player_data["created_at"].year, player_data["created_at"].month, player_data["created_at"].day),
            "$lt": datetime(player_data["created_at"].year, player_data["created_at"].month, player_data["created_at"].day) + timedelta(days=1)
        }
    })
    if existing_record: # Update the existing record
        await collection.update_one({
            "_id": existing_record["_id"]
        }, {
            "$set": player_data
        })
        return {"id": str(existing_record["_id"])}
    result = await collection.insert_one(player_data)
    return {"id": str(result.inserted_id)}

@router.get("/players")
async def get_players(db=Depends(get_db),user=Depends(verify_jwt)):
    collection = db["entries"]
    players = []
    async for player in collection.find({"email": user['email']}).sort("created_at", -1):
        players.append(fix_object_id(player))
    return players

@router.get("/visualize/", response_class=HTMLResponse)  # change matplotlib to plotly
async def visualize(db=Depends(get_db),current_user=Depends(verify_jwt)):
    collection = db["entries"]

    # Find all records for the current user this month
    now = datetime.now()

    # Create a datetime object representing the first day of this month
    first_day_this_month = datetime(now.year, now.month, 1)

    # Create a datetime object representing the first day of next month
    if now.month == 12:
        first_day_next_month = datetime(now.year + 1, 1, 1)
    else:
        first_day_next_month = datetime(now.year, now.month + 1, 1)

    # Find all records for the current user this month
    player_records = await collection.find({
        "email": current_user['email'],
        "created_at": {
            "$gte": first_day_this_month,
            "$lt": first_day_next_month
        }
    }).to_list(length=100)
    # player_records = await collection.find({"email": current_user['email']}).to_list(length=100)

    if not player_records:
        return "No records found for this player"

    # Create a list of goals and assists
    goals = [record["goals"] for record in player_records]
    assists = [record["assists"] for record in player_records]
    dates= [date2num(record["created_at"]) for record in player_records]
    plt.figure(figsize=(12, 6))
    # Create a line graph
    plt.plot_date(dates, goals, label='Goals', linestyle='solid', marker='None')
    plt.plot_date(dates, assists, label='Assists', linestyle='solid', marker='None')
    plt.title(f'Goals and Assists for {current_user["email"]}')
    date_format = DateFormatter('%m-%d')
    plt.gca().xaxis.set_major_formatter(date_format)
    plt.ylabel('Count')
    plt.legend()

    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Encode the BytesIO object to base64 and embed it in HTML
    string = base64.b64encode(buf.read())
    uri = 'data:image/png;base64,' + urllib.parse.quote(string)
    html = '<img src = "%s"/>' % uri

    return html

