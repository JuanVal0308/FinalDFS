import os
import bcrypt
import jwt

from fastapi import HTTPException, Header
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "changeme-secret")


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    )


def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(
        password.encode(),
        hashed
    )


def create_token(username: str) -> str:
    token = jwt.encode(
        {"username": username},
        JWT_SECRET,
        algorithm="HS256"
    )
    return token


def verify_token(authorization: str = Header(...)) -> str:
    """
    Extrae y valida el JWT del header Authorization: Bearer <token>.
    Retorna el username si el token es válido.
    Lanza HTTP 401 si el token es inválido o está ausente.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or malformed. Use: Bearer <token>"
        )

    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["username"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
