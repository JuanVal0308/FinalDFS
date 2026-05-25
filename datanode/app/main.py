import os
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response

from app.storage import save_block, read_block, delete_block, list_blocks

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("datanode")

NODE_ID = os.getenv("NODE_ID", "datanode-unknown")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DFS DataNode",
    version="2.0.0",
    description=f"Nodo de datos"
)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "DFS DataNode",
        "node_id": NODE_ID,
        "status": "running",
        "blocks_stored": len(list_blocks())
    }


@app.post("/block/upload/{block_id}", tags=["Blocks"])
async def upload_block(
    block_id: str,
    file: UploadFile = File(...)
):
    """Recibe y almacena un bloque de datos en disco."""
    data = await file.read()
    save_block(block_id, data)
    logger.info(f"Bloque almacenado: {block_id} ({len(data)} bytes)")
    return {
        "message": "Block stored",
        "block_id": block_id,
        "size_bytes": len(data)
    }


@app.get("/block/{block_id}", tags=["Blocks"])
def get_block(block_id: str):
    """Descarga un bloque almacenado en este DataNode."""
    data = read_block(block_id)
    if data is None:
        logger.warning(f"Bloque no encontrado: {block_id}")
        raise HTTPException(status_code=404, detail="Block not found")

    logger.info(f"Bloque servido: {block_id} ({len(data)} bytes)")
    return Response(
        content=data,
        media_type="application/octet-stream"
    )


@app.delete("/block/{block_id}", tags=["Blocks"])
def remove_block(block_id: str):
    """Elimina un bloque del disco de este DataNode."""
    existed = delete_block(block_id)
    if not existed:
        raise HTTPException(status_code=404, detail="Block not found")

    logger.info(f"Bloque eliminado: {block_id}")
    return {"message": "Block deleted", "block_id": block_id}


@app.get("/blocks", tags=["Blocks"])
def get_all_blocks():
    """Lista todos los block_ids almacenados en este DataNode."""
    blocks = list_blocks()
    return {"node_id": NODE_ID, "blocks": blocks, "count": len(blocks)}
