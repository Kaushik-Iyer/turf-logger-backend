from fastapi import FastAPI,Depends,HTTPException
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from .routers import players, comparisons
import os
from starlette.responses import RedirectResponse, FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
import pandas as pd
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pdb

load_dotenv()
maps_api_key=os.getenv('MAPS_API_KEY')
football_data_org_api_key=os.getenv('FOOTBALL_DATA_ORG_API_KEY')


mongo_password=os.getenv('MONGO_PASSWORD')
uri = f"mongodb+srv://kaushikiyer:{mongo_password}@project.sfu2jan.mongodb.net/?retryWrites=true&w=majority&appName=Project"

def get_current_user(request: Request):
    user = request.session.get('user')
    if user is None:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user

class User(BaseModel):
    google_id: str
    email: str
    name: str
    profile_pic_url: str

app = FastAPI()
origins = [
    "http://localhost:3000"
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

def get_current_user(request: Request):
    user = request.session.get('user')
    if user is None:
        return None
    return user

@app.on_event("startup")
async def on_startup():
    app.state.client = AsyncIOMotorClient(uri)
    app.state.player = pd.read_csv('backend/appearances.csv')
    app.state.users = app.state.client["TestDB"]["users"]

@app.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')  # Get the URL for the /auth endpoint
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth')
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    request.session['user'] = user_info

    user=User(google_id=user_info['sub'], email=user_info['email'], name=user_info['name'], profile_pic_url=user_info['picture'])
    await app.state.users.update_one({'google_id': user.google_id}, {'$set': user.dict()}, upsert=True)
    return RedirectResponse(url='http://localhost:3000/players')

@app.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return {"message": "Logged out"}

@app.get('/user')
async def user(request: Request):
    user = request.session.get('user')
    if user is None:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user

@app.get('/')
async def root(current_user=Depends(get_current_user)):
    if current_user:
        return {"loggedIn": True}
    else:
        return {"loggedIn": False}
#check if user is logged in, redirect to /players if logged in, else redirect to /login
