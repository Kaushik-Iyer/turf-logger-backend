from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from .temp import verify_jwt,fix_object_id
from starlette.requests import Request
from datetime import datetime

def get_db(request: Request):
    db = request.app.state.client["TestDB"]
    return db


class Point(BaseModel):
    x: float
    y: float


class Line(BaseModel):
    start: Point
    end: Point

class Drawing(BaseModel):
    image: str
    passes: List[Line]
    shots: List[Line]


router = APIRouter()


@router.post("/pitch")
async def create_pitch(drawing: Drawing,user=Depends(verify_jwt), db=Depends(get_db)):
    collection = db["pitches"]
    drawing = drawing.dict()
    drawing["email"] = user["email"]
    drawing["created_at"] = datetime.now()
    result = await collection.insert_one(drawing)
    return {"message": "Pitch created successfully.", "id": str(result.inserted_id)}

@router.get("/shots")
async def get_shots(db=Depends(get_db), user=Depends(verify_jwt)):
    collection = db["pitches"]
    shots = []
    async for shot in collection.find({"email": user["email"]},{"image":0,"passes":0,"email":0}):
        shots.append(fix_object_id(shot))
    return shots
