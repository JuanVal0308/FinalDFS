import os
import bcrypt
import jwt

from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")

def hash_password(password: str):

    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    )

def verify_password(password: str, hashed: bytes):

    return bcrypt.checkpw(
        password.encode(),
        hashed
    )

def create_token(username: str):

    token = jwt.encode(
        {"username": username},
        JWT_SECRET,
        algorithm="HS256"
    )

    return token
