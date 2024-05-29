
from fastapi import APIRouter,Depends
from pydantic import BaseModel
from .players import get_db
from .temp import verify_jwt,fix_object_id

router = APIRouter()


class Injury(BaseModel):
    injury_type: str
    duration: int

@router.post('/injuries')
async def post_injury(injury:Injury,user=Depends(verify_jwt),db=Depends(get_db)):  
    collection=db["injuries"]
    injury=injury.dict()
    injury["email"]=user["email"]
    result=await collection.insert_one(injury)
    return {"id":str(result.inserted_id)}

@router.get("/injuries")
async def get_injuries(db=Depends(get_db),user=Depends(verify_jwt)):
    collection=db["injuries"]
    injuries=[]
    async for injury in collection.find({"email":user["email"]}):
        injuries.append(fix_object_id(injury))
    return injuries
