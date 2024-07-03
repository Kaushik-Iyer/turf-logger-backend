from fastapi import FastAPI, HTTPException
from starlette.requests import Request
from dotenv import load_dotenv
from .routers import players, comparisons, injuries, pitch
import os
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
import requests

load_dotenv()
maps_api_key = os.getenv('MAPS_API_KEY')
football_data_org_api_key = os.getenv('FOOTBALL_DATA_ORG_API_KEY')
secret_key = os.getenv('SECRET_KEY')
mongo_password = os.getenv('MONGO_PASSWORD')
algorithm = "HS256"
uri = f"mongodb+srv://kaushikiyer:{mongo_password}@project.sfu2jan.mongodb.net/?retryWrites=true&w=majority&appName=Project"


def get_current_user(request: Request):
    user = request.session.get('user')
    if user is None:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user


def document_to_dict(document):
    # Convert ObjectId to str
    document['_id'] = str(document['_id'])
    return document


class Token(BaseModel):
    access_token: str


app = FastAPI(debug=True)
origins = [
    "http://localhost:3000",
    "https://turf-logger-frontend.pages.dev",
    "https://myfootballstats.social"
]
app.include_router(players.router)
app.include_router(comparisons.router)
app.include_router(injuries.router)
app.include_router(pitch.router)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])
app.add_middleware(SessionMiddleware, secret_key=os.getenv('SECRET_KEY'))


def verify_google_token(token: str):
    try:
        response = requests.get('https://www.googleapis.com/oauth2/v3/tokeninfo?access_token=' + token)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        raise HTTPException(status_code=401, detail='Invalid token')


@app.on_event("startup")
async def on_startup():
    app.state.client = AsyncIOMotorClient(uri)
    # app.state.player = pd.read_csv('backend/appearances.csv')
    app.state.users = app.state.client["TestDB"]["users"]


@app.post('/auth/google')
async def auth_google(token: Token):
    google_data = verify_google_token(token.access_token)
    if not google_data:
        raise HTTPException(status_code=401, detail='Invalid token')

    # Get user's profile information from Google
    headers = {'Authorization': f'Bearer {token.access_token}'}
    response = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail='Failed to get user info')
    user_info = response.json()

    user = await app.state.users.find_one({'email': user_info['email']})
    if user is None:
        user = {
            'email': user_info['email'],
            'name': user_info['name'],
            'profile_pic_url': user_info['picture']
        }
        await app.state.users.insert_one(user)
    email = user_info['email']
    payload = {'email': email}
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return {'access_token': token, 'token_type': 'bearer'}


@app.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return {"message": "Logged out"}
