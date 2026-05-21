from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response

from app.storage import (
    save_block,
    read_block
)

app = FastAPI(
    title="DFS DataNode",
    version="1.0.0"
)

@app.get("/")
def root():

    return {
        "service": "DFS DataNode",
        "status": "running"
    }

@app.post("/block/upload/{block_id}")
async def upload_block(
    block_id: str,
    file: UploadFile = File(...)
):

    data = await file.read()

    save_block(
        block_id,
        data
    )

    return {
        "message": "Block stored",
        "block_id": block_id
    }

@app.get("/block/{block_id}")
def get_block(block_id: str):

    data = read_block(block_id)

    if not data:

        raise HTTPException(
            status_code=404,
            detail="Block not found"
        )

    return Response(
        content=data,
        media_type="application/octet-stream"
    )
