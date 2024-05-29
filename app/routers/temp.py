import os
from pydantic import BaseModel
import geocoder
from typing import Optional
import jwt
from jose import JWTError
from dotenv import load_dotenv
from fastapi import HTTPException , Header
from starlette.requests import Request
from fastapi.security import OAuth2PasswordBearer
load_dotenv()
maps_api_key=os.getenv('MAPS_API_KEY')
secret_key=os.getenv('SECRET_KEY')
algorithm="HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def fix_object_id(doc):
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def get_lat_long():
    g=geocoder.ip('me')
    return g.latlng

def get_current_user(request: Request):
    user = request.session.get('user')
    return user

def verify_jwt(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=403, detail='Authorization header is missing')
    
    scheme, _, token = authorization.partition(' ')
    
    if scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Invalid authorization scheme')
    
    if not token:
        raise HTTPException(status_code=403, detail='Token is missing')
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

class Player(BaseModel):
    position: str
    goals: int
    assists: int

    def model_dump(self):
        return {
            "position": self.position,
            "goals": self.goals,
            "assists": self.assists
        }

