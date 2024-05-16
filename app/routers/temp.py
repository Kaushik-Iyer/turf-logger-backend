import os
from pydantic import BaseModel
import geocoder
from dotenv import load_dotenv
from fastapi import HTTPException
from starlette.requests import Request
load_dotenv()
maps_api_key=os.getenv('MAPS_API_KEY')

def fix_object_id(doc):
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def get_lat_long():
    g=geocoder.ip('me')
    return g.latlng

def get_current_user(request: Request):
    user = request.session.get('user')
    if user is None:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user

class Player(BaseModel):
    name: str
    goals: int
    assists: int

    def model_dump(self):
        return {
            "name": self.name,
            "goals": self.goals,
            "assists": self.assists
        }

