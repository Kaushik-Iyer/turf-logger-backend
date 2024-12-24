from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .players import get_db
from .temp import verify_jwt, fix_object_id
from datetime import datetime

router = APIRouter()

class InjurySpot(BaseModel):
    """
    A model representing an injury spot.

    Attributes:
        x_coordinate (float): The x-coordinate of the injury spot.
        y_coordinate (float): The y-coordinate of the injury spot.
    """
    x: float
    y: float

# Define the Injury model
class Injury(BaseModel):
    """
    A model representing an injury.

    Attributes:
        injury_type (str): The type of the injury.
        duration (int): The duration of the injury in days.
    """
    injury_type: str
    duration: int
    location: InjurySpot




# Route to create a new injury
@router.post('/injuries')
async def post_injury(injury: Injury, user=Depends(verify_jwt), db=Depends(get_db)):
    """
    Create a new injury.

    Args:
        injury (Injury): The injury to create.
        user (dict): The authenticated user.
        db (Database): The database connection.

    Returns:
        dict: A dictionary containing the ID of the created injury.
    """
    collection = db["injuries"]
    injury = injury.dict()
    injury["email"] = user["email"]
    injury["created_at"] = datetime.now()
    result = await collection.insert_one(injury)
    injury_id = str(result.inserted_id)
    injury_spot_collection = db["injury_spots"]
    injury_spot_data = injury["location"]
    injury_spot_data["injury_id"] = injury_id
    await injury_spot_collection.insert_one(injury_spot_data)

    return {"id": injury_id}

# Route to get all injuries
@router.get("/injuries")
async def get_injuries(db=Depends(get_db), user=Depends(verify_jwt)):
    """
    Get all injuries for the authenticated user.

    Args:
        db (Database): The database connection.
        user (dict): The authenticated user.

    Returns:
        list: A list of injuries.
    """
    collection = db["injuries"]
    injuries = []
    async for injury in collection.find({"email": user["email"]}):
        injuries.append(fix_object_id(injury))
        injury_spots = db["injury_spots"].find({"injury_id": str(injury["_id"])})
        injury["injury_spots"] = []
        async for spot in injury_spots:
            injury["injury_spots"].append(fix_object_id(spot))
    return injuries


# Route to update an injury
@router.put('/injuries/{injury_id}')
async def update_injury(injury_id: str, injury: Injury, user=Depends(verify_jwt), db=Depends(get_db)):
    """
    Update an existing injury.

    Args:
        injury_id (str): The ID of the injury to update.
        injury (Injury): The updated injury.
        user (dict): The authenticated user.
        db (Database): The database connection.

    Returns:
        dict: A dictionary containing a success message.
    """
    collection = db["injuries"]
    injury = injury.dict()
    injury["email"] = user["email"]
    result = await collection.update_one({"_id": injury_id, "email": user["email"]}, {"$set": injury})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Injury not found")
    return {"message": "Injury updated successfully"}


# Route to delete an injury
@router.delete('/injuries/{injury_id}')
async def delete_injury(injury_id: str, user=Depends(verify_jwt), db=Depends(get_db)):
    """
    Delete an existing injury.

    Args:
        injury_id (str): The ID of the injury to delete.
        user (dict): The authenticated user.
        db (Database): The database connection.

    Returns:
        dict: A dictionary containing a success message.
    """
    collection = db["injuries"]
    result = await collection.delete_one({"_id": injury_id, "email": user["email"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Injury not found")
    return {"message": "Injury deleted successfully"}
