from fastapi import FastAPI,Depends,HTTPException
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from .routers import players, comparisons
import os
from starlette.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorClient
import pandas as pd
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
import requests
from fastapi.security import OAuth2PasswordBearer

load_dotenv()
maps_api_key=os.getenv('MAPS_API_KEY')
football_data_org_api_key=os.getenv('FOOTBALL_DATA_ORG_API_KEY')
secret_key=os.getenv('SECRET_KEY')
mongo_password=os.getenv('MONGO_PASSWORD')
algorithm="HS256"
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

class User(BaseModel):
    email: str
    name: str
    profile_pic_url: str

class Token(BaseModel):
    access_token: str

class TokenData(BaseModel):
    email: str


app = FastAPI()
origins = [
    "http://localhost:3000",
    "https://turf-logger-frontend.pages.dev",
    "https://myfootballstats.social"
]
app.include_router(players.router)
app.include_router(comparisons.router)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SessionMiddleware, secret_key= os.getenv('SECRET_KEY'))
config=Config('.env')
oauth=OAuth(config)
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    authorize_params=None,
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri='http://localhost:8000/auth',  
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
)

def verify_google_token(token:str):
    try:
        response=requests.get('https://www.googleapis.com/oauth2/v3/tokeninfo?access_token='+token)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=401, detail='Invalid token')


@app.on_event("startup")
async def on_startup():
    app.state.client = AsyncIOMotorClient(uri)
    # app.state.player = pd.read_csv('backend/appearances.csv')
    app.state.users = app.state.client["TestDB"]["users"]

@app.post('/login')
async def login(user: User, request: Request):
    db_user = await app.state.users.find_one({'email': user.email})
    if db_user is None:
        raise HTTPException(status_code=401, detail='User not found')
    db_user = document_to_dict(db_user)
    request.session['user'] = db_user
    return {"message": "Logged in"}

@app.post('/auth/google')
async def auth_google(token: Token):
    google_data = verify_google_token(token.access_token)
    if not google_data:
        raise HTTPException(status_code=401, detail='Invalid token')
    user = await app.state.users.find_one({'email': google_data['email']})
    if user is None:
        user = {
            'email': google_data['email'],
            'name': google_data['name'],
            'profile_pic_url': google_data['picture']
        }
        await app.state.users.insert_one(user)
    email = google_data['email']
    payload = {'email': email}
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return {'access_token': token, 'token_type': 'bearer'}
    
@app.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return {"message": "Logged out"}

