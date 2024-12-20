from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bson import ObjectId
from .temp import verify_jwt

class FriendRequest(BaseModel):
    sender_email: str
    recipient_email: str
    status: str  # "pending", "accepted", "rejected"
    created_at: datetime
    updated_at: Optional[datetime]

def get_db(request: Request):
    return request.app.state.client["TestDB"]

router = APIRouter()

@router.post('/request/{recipient_email}')
async def send_friend_request(recipient_email: str, db=Depends(get_db), user=Depends(verify_jwt)):
    # Validate recipient exists
    recipient = await db.users.find_one({'email': recipient_email})
    if not recipient:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if request already exists
    existing_request = await db.friend_requests.find_one({
        'sender_email': user['email'],
        'recipient_email': recipient_email,
        'status': 'pending'
    })
    if existing_request:
        raise HTTPException(status_code=400, detail="Request already sent")

    request = {
        'sender_email': user['email'],
        'recipient_email': recipient_email,
        'status': 'pending',
        'created_at': datetime.utcnow()
    }
    await db.friend_requests.insert_one(request)
    return {"message": "Friend request sent"}

@router.post('/accept/{request_id}')
async def accept_friend_request(request_id: str, db=Depends(get_db), user=Depends(verify_jwt)):
    request = await db.friend_requests.find_one({'_id': ObjectId(request_id)})
    if not request or request['recipient_email'] != user['email']:
        raise HTTPException(status_code=404, detail="Request not found")
    
    await db.friend_requests.update_one(
        {'_id': ObjectId(request_id)},
        {
            '$set': {
                'status': 'accepted',
                'updated_at': datetime.utcnow()
            }
        }
    )
    
    friendship = {
        'user1_email': request['sender_email'],
        'user2_email': request['recipient_email'],
        'created_at': datetime.utcnow()
    }
    await db.friendships.insert_one(friendship)
    
    return {"message": "Friend request accepted"}

@router.get('/list')
async def get_friends(db=Depends(get_db), user=Depends(verify_jwt)):
    friendships = await db.friendships.find({
        '$or': [
            {'user1_email': user['email']},
            {'user2_email': user['email']}
        ]
    }).to_list(length=None)
    
    friend_emails = []
    for friendship in friendships:
        friend_email = friendship['user2_email'] if friendship['user1_email'] == user['email'] else friendship['user1_email']
        friend_emails.append(friend_email)
    
    friends = await db.users.find({
        'email': {'$in': friend_emails}
    }).to_list(length=None)
    
    return [{'email': f['email'], 'name': f['name'], 'profile_pic_url': f['profile_pic_url']} for f in friends]

@router.get('/requests')
async def get_friend_requests(db=Depends(get_db), user=Depends(verify_jwt)):
    requests = await db.friend_requests.find({
        'recipient_email': user['email'],
        'status': 'pending'
    }).to_list(length=None)
    
    for request in requests:
        sender = await db.users.find_one({'email': request['sender_email']})
        request['sender'] = {
            'email': sender['email'],
            'name': sender['name'],
            'profile_pic_url': sender['profile_pic_url']
        }
        request['_id'] = str(request['_id'])  # Convert ObjectId to string
    
    return requests

@router.get("/visualize/{friend_email}")
async def visualize_friend(
    friend_email: str, 
    db=Depends(get_db), 
    user=Depends(verify_jwt),
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    compare: bool = False
):
    # Verify friendship
    friendship = await db.friendships.find_one({
        '$or': [
            {'user1_email': user['email'], 'user2_email': friend_email},
            {'user1_email': friend_email, 'user2_email': user['email']}
        ]
    })
    
    if not friendship:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's stats")

    # Build query
    query = {}
    if start_date and end_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        query["created_at"] = {
            "$gte": start_date_obj,
            "$lt": end_date_obj
        }

    # Get friend's records
    friend_records = await db.entries.find({
        **query,
        "email": friend_email
    }).sort("created_at", 1).to_list(length=100)

    response = {
        "friend": {
            "name": (await db.users.find_one({"email": friend_email}))["name"],
            "dates": [record["created_at"].isoformat() for record in friend_records],
            "goals": [record["goals"] for record in friend_records],
            "assists": [record["assists"] for record in friend_records]
        }
    }

    if compare:
        # Get current user's records
        user_records = await db.entries.find({
            **query,
            "email": user["email"]
        }).sort("created_at", 1).to_list(length=100)

        response["user"] = {
            "name": (await db.users.find_one({"email": user["email"]}))["name"],
            "dates": [record["created_at"].isoformat() for record in user_records],
            "goals": [record["goals"] for record in user_records],
            "assists": [record["assists"] for record in user_records]
        }

    return response