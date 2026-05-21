from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.database import (
    users_collection,
    files_collection
)

from app.models import FileMetadata

from app.auth import (
    hash_password,
    verify_password,
    create_token
)

app = FastAPI(
    title="DFS NameNode",
    version="1.0.0"
)

DATANODES = [
    "http://52.23.74.126:8001",
    "http://52.23.74.126:8002",
    "http://52.23.74.126:8003"
]

class UserRegister(BaseModel):
    username: str
    password: str


@app.get("/")
def root():

    return {
        "service": "DFS NameNode",
        "status": "running"
    }


@app.post("/auth/register")
def register(user: UserRegister):

    existing = users_collection.find_one({
        "username": user.username
    })

    if existing:

        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    hashed = hash_password(user.password)

    users_collection.insert_one({
        "username": user.username,
        "password": hashed
    })

    return {
        "message": "User created"
    }


@app.post("/auth/login")
def login(user: UserRegister):

    existing = users_collection.find_one({
        "username": user.username
    })

    if not existing:

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    valid = verify_password(
        user.password,
        existing["password"]
    )

    if not valid:

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_token(
        user.username
    )

    return {
        "token": token
    }


@app.post("/files/register")
def register_file(file: FileMetadata):

    files_collection.insert_one({
        "filename": file.filename,
        "blocks": [
            {
                "block_id": block.block_id,
                "replicas": block.replicas
            }
            for block in file.blocks
        ]
    })

    return {
        "message": "File registered"
    }

@app.get("/files/{filename}")
def get_file(filename: str):

    file = files_collection.find_one({
        "filename": filename
    })

    if not file:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return {
        "filename": file["filename"],
        "blocks": file["blocks"]
    }

@app.get("/files/allocate/{filename}/{num_blocks}")
def allocate_file(
    filename: str,
    num_blocks: int
):

    blocks = []

    total_nodes = len(DATANODES)

    for i in range(num_blocks):

        block_id = f"{filename}_block{i}"

        primary = DATANODES[
            i % total_nodes
        ]

        replica = DATANODES[
            (i + 1) % total_nodes
        ]

        blocks.append({
            "block_id": block_id,
            "replicas": [
                primary,
                replica
            ]
        })

    return {
        "filename": filename,
        "blocks": blocks
    }
