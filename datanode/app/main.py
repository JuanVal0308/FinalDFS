import os
import logging
import threading
import time

import requests
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

PUBLIC_IP = os.getenv("PUBLIC_IP", "52.23.74.126")
NODE_ID = os.getenv("NODE_ID", "datanode-unknown")
NAMENODE_URL = os.getenv("NAMENODE_URL", "http://namenode:8000")

_PORT_MAP = {"datanode1": "8001", "datanode2": "8002", "datanode3": "8003"}
_DEFAULT_PORT = _PORT_MAP.get(NODE_ID, os.getenv("PORT", "8001"))
NODE_PUBLIC_URL = os.getenv(
    "NODE_PUBLIC_URL",
    f"http://{PUBLIC_IP}:{_DEFAULT_PORT}",
)
HEARTBEAT_INTERVAL_SEC = int(os.getenv("HEARTBEAT_INTERVAL_SEC", "30"))

# ---------------------------------------------------------------------------
# Heartbeat hacia el NameNode
# ---------------------------------------------------------------------------

def register_with_namenode() -> bool:
    try:
        resp = requests.post(
            f"{NAMENODE_URL}/datanodes/register",
            json={"node_id": NODE_ID, "url": NODE_PUBLIC_URL},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info(f"Registrado en NameNode: {NODE_ID} -> {NODE_PUBLIC_URL}")
        return True
    except Exception as e:
        logger.error(f"No se pudo registrar en NameNode: {e}")
        return False


def send_heartbeat() -> None:
    try:
        requests.post(
            f"{NAMENODE_URL}/datanodes/heartbeat",
            json={"node_id": NODE_ID, "blocks": list_blocks()},
            timeout=10,
        ).raise_for_status()
        logger.debug(f"Heartbeat enviado: {NODE_ID}")
    except Exception as e:
        logger.warning(f"Heartbeat fallido: {e}")


def heartbeat_loop() -> None:
    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL_SEC)


def start_heartbeat_thread() -> None:
    def _run():
        for attempt in range(10):
            if register_with_namenode():
                heartbeat_loop()
                return
            logger.warning(f"Reintento de registro {attempt + 1}/10 en 5s...")
            time.sleep(5)
        logger.error("Heartbeat no iniciado: registro en NameNode falló")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    logger.info(
        f"Hilo de heartbeat iniciado (cada {HEARTBEAT_INTERVAL_SEC}s -> {NAMENODE_URL})"
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DFS DataNode",
    version="2.0.0",
    description="Nodo de datos"
)


@app.on_event("startup")
def on_startup():
    start_heartbeat_thread()


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
