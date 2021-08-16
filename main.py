from fastapi import FastAPI, HTTPException, Request
from os import environ as env
from pymongo import MongoClient
from argon2 import PasswordHasher, Type
from itsdangerous.url_safe import URLSafeSerializer
from snowflake import Generator as SnowflakeGenerator
from datetime import datetime, timezone
from string import ascii_letters


app = FastAPI()

# Database
mongo = MongoClient(env["mongo_uri"])
db = mongo["blue"]
user_login_collection = db["users_login"]
users_collection = db["users"]

# Hashing
password_hasher = PasswordHasher()
serializer = URLSafeSerializer(env["SECRET_KEY"], salt="auth")

# Serializer
epoch = datetime(year=2020, month=1, day=1, tzinfo=timezone.utc)
epoch = int(epoch.timestamp())
snowflake = SnowflakeGenerator(epoch=epoch)

acceptable_chars = ["_", "-", *ascii_letters]

def is_valid_username(username):
    for char in list(username):
        if char not in  acceptable_chars:
            return False
    return True

@app.post("/login")
async def login(request: Request):
    username = request.headers["username"]
    password = request.headers["password"]

    if (user_login := user_login_collection.find_one({"username": username})) is None:
        raise HTTPException(detail="User not found.", status_code=400)
    try:
        assert password_hasher.verify(user_login["password"], password)
    except Exception as e:
        raise HTTPException(detail="Invalid password", status_code=400)
    token = serializer.dumps({"user_id": user_login["_id"], "password_change_id": user_login["password_change_id"]})
    return {"token": token}

@app.post("/register")
async def register(request: Request):
    username = request.headers["username"]
    password = request.headers["password"]
    
    # Verify username
    if user_login_collection.find_one({"username": username}) is not None:
        raise HTTPException(detail="Username is taken.", status_code=400)
    if not is_valid_username(username):
        raise HTTPException(detail="Username contains invalid characters.", status_code=400)

    # Generate user info
    user_id = int(snowflake.generate())
    user_login = {
        "_id": user_id,
        "username": username,
        "password": password_hasher.hash(password),
        "password_change_id": 0,
    }
    user = {
        "_id": user_id,
        "username": username,
        "interests": {}
    }

    user_login_collection.insert_one(user_login)
    users_collection.insert_one(user)

    # Create a token
    token = serializer.dumps({"user_id": user_id, "password_change_id": 0})

    return {"token": token}

