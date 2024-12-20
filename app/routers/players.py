from fastapi import APIRouter, Depends
from .temp import fix_object_id, Player, verify_jwt
from datetime import datetime, timedelta

from starlette.requests import Request
from pydantic import BaseModel
from bson import ObjectId
from typing import Optional
from datetime import datetime
from fastapi import HTTPException
class Suggestion(BaseModel):
    suggestion: str


def get_db(request: Request):
    db = request.app.state.client["TestDB"]
    return db

router = APIRouter()


@router.post("/entries")
async def create_player(player: Player, db=Depends(get_db), user=Depends(verify_jwt)):
    collection = db["entries"]
    player_data = player.model_dump()
    player_data["created_at"] = datetime.now()
    player_data["email"] = user['email']
    # Find existing record with the same email and created_at date
    existing_record = await collection.find_one({
        "email": user['email'],
        "created_at": {
            "$gte": datetime(player_data["created_at"].year, player_data["created_at"].month,
                             player_data["created_at"].day),
            "$lt": datetime(player_data["created_at"].year, player_data["created_at"].month,
                            player_data["created_at"].day) + timedelta(days=1)
        }
    })
    if existing_record:  # Update the existing record
        await collection.update_one({
            "_id": existing_record["_id"]
        }, {
            "$set": player_data
        })
        return {"id": str(existing_record["_id"])}
    result = await collection.insert_one(player_data)
    return {"id": str(result.inserted_id)}


# Delete a player record
@router.delete("/entries/{player_id}")
async def delete_player(player_id: str, db=Depends(get_db), user=Depends(verify_jwt)):
    collection = db["entries"]
    result = await collection.delete_one({
        "_id": ObjectId(player_id),
        "email": user['email']
    })
    if result.deleted_count == 1:
        return {"message": "Entry deleted successfully"}
    return {"message": "Entry not found"}


@router.get("/players")
async def get_players(db=Depends(get_db), user=Depends(verify_jwt),start_date: Optional[str] = None, end_date: Optional[str] = None):
    collection = db["entries"]
    players = []
    query = {
        "email": user['email']
    }
    if start_date and end_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        query["created_at"] = {
            "$gte": start_date_obj,
            "$lt": end_date_obj
        }
    result = await collection.find(query).sort("created_at", -1).to_list(length=100)
    for player in result:
        players.append(fix_object_id(player))
    return players


@router.get("/visualize/") 
async def visualize(db=Depends(get_db), current_user=Depends(verify_jwt), start_date: Optional[str] = None, end_date: Optional[str] = None):
    collection = db["entries"]
    query = {
        "email": current_user['email']
    }
    if start_date and end_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        query["created_at"] = {
            "$gte": start_date_obj,
            "$lt": end_date_obj
        }
    player_records = await collection.find(query).sort("created_at", 1).to_list(length=100)

    if len(player_records) < 2:
        return "No records found for this player"

    # Create a list of goals and assists
    goals = [record["goals"] for record in player_records]
    assists = [record["assists"] for record in player_records]
    dates = [record["created_at"].isoformat() for record in player_records]
    return {"dates": dates, "goals": goals, "assists": assists}


@router.post('/suggestions')
async def create_suggestion(suggestion: Suggestion, user=Depends(verify_jwt), db=Depends(get_db)):
    collection = db["suggestions"]
    suggestion_data = suggestion.dict()
    suggestion_data["email"] = user['email']
    result = await collection.insert_one(suggestion_data)
    return {"id": str(result.inserted_id)}

@router.get("/profile")
async def get_profile(user=Depends(verify_jwt), db=Depends(get_db)):
    user = await db["users"].find_one({"email": user["email"]})
    return fix_object_id(user)

