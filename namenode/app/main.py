import os
import io
import logging
import threading
import time
import requests
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel

from app.database import (
    users_collection,
    files_collection,
    directories_collection,
    datanodes_collection,
)
from app.models import FileMetadata, DataNodeRegister, DataNodeHeartbeat
from app.auth import hash_password, verify_password, create_token, verify_token

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("namenode")

# ---------------------------------------------------------------------------
# Configuración desde variables de entorno
# ---------------------------------------------------------------------------

# IP pública EC2 — NameNode :8000, DataNodes :8001-:8003
PUBLIC_IP = os.getenv("PUBLIC_IP", "52.23.74.126")
_DEFAULT_PUBLIC_DATANODES = (
    f"http://{PUBLIC_IP}:8001,"
    f"http://{PUBLIC_IP}:8002,"
    f"http://{PUBLIC_IP}:8003"
)

# URLs internas Docker — comunicación contenedor-a-contenedor (heartbeat, re-replicación)
_raw_internal = os.getenv(
    "DATANODES",
    "http://datanode1:8001,http://datanode2:8001,http://datanode3:8001",
)
DATANODES_INTERNAL = [url.strip() for url in _raw_internal.split(",")]

# URLs públicas — devueltas al cliente en /allocate
_raw_public = os.getenv("PUBLIC_DATANODES", _DEFAULT_PUBLIC_DATANODES)
DATANODES_PUBLIC = [url.strip() for url in _raw_public.split(",")]

logger.info(f"DataNodes internos : {DATANODES_INTERNAL}")
logger.info(f"DataNodes públicos : {DATANODES_PUBLIC}")

HEARTBEAT_TIMEOUT_SEC = int(os.getenv("HEARTBEAT_TIMEOUT_SEC", "90"))
MONITOR_INTERVAL_SEC = int(os.getenv("MONITOR_INTERVAL_SEC", "30"))

# Mapa público→interno para que el NameNode use hostnames Docker al llamar a los DataNodes
# Ejemplo: "http://52.x.x.x:8001" → "http://datanode1:8001"
PUBLIC_TO_INTERNAL: dict[str, str] = dict(zip(DATANODES_PUBLIC, DATANODES_INTERNAL))


def internal_url(public_replica: str) -> str:
    """Traduce una URL pública de réplica a su equivalente interno Docker."""
    return PUBLIC_TO_INTERNAL.get(public_replica, public_replica)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_allocation_datanodes() -> list[str]:
    """DataNodes vivos registrados; si no hay suficientes, usa la lista pública configurada."""
    alive = [
        d["url"]
        for d in datanodes_collection.find({"status": "alive"}).sort("node_id", 1)
    ]
    if len(alive) >= 2:
        return alive
    return DATANODES_PUBLIC


def serialize_datanode(doc: dict) -> dict:
    last_seen = doc.get("last_seen")
    if isinstance(last_seen, datetime):
        last_seen = last_seen.isoformat()
    return {
        "node_id": doc["node_id"],
        "url": doc["url"],
        "status": doc.get("status", "unknown"),
        "last_seen": last_seen,
        "blocks_count": len(doc.get("blocks", [])),
    }


def rereplicate_blocks_on_dead_node(dead_url: str) -> None:
    """Copia bloques huérfanos desde una réplica viva hacia otro DataNode activo."""
    alive_nodes = list(datanodes_collection.find({"status": "alive"}))
    alive_urls = {n["url"] for n in alive_nodes}

    if not alive_urls:
        logger.error("Re-replicación abortada: no hay DataNodes vivos")
        return

    logger.info(f"Iniciando re-replicación por caída de {dead_url}")

    for file_doc in files_collection.find({}):
        updated_blocks = []
        file_changed = False

        for block in file_doc["blocks"]:
            replicas = block["replicas"]
            if dead_url not in replicas:
                updated_blocks.append(block)
                continue

            survivors = [r for r in replicas if r != dead_url]
            source_url = None
            block_data = None

            for url in survivors:
                try:
                    resp = requests.get(
                        f"{internal_url(url)}/block/{block['block_id']}",
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        source_url = url
                        block_data = resp.content
                        break
                except Exception as e:
                    logger.warning(
                        f"Réplica {url} no disponible para {block['block_id']}: {e}"
                    )

            if block_data is None:
                logger.error(
                    f"No se pudo leer {block['block_id']} desde réplicas sobrevivientes"
                )
                updated_blocks.append(block)
                continue

            target_url = None
            for node in alive_nodes:
                candidate = node["url"]
                if candidate != dead_url and candidate not in replicas:
                    target_url = candidate
                    break

            if target_url is None:
                for node in alive_nodes:
                    if node["url"] != dead_url:
                        target_url = node["url"]
                        break

            if target_url is None:
                logger.error(f"Sin DataNode destino para re-replicar {block['block_id']}")
                updated_blocks.append(block)
                continue

            try:
                requests.post(
                    f"{internal_url(target_url)}/block/upload/{block['block_id']}",
                    files={
                        "file": (
                            block["block_id"],
                            io.BytesIO(block_data),
                            "application/octet-stream",
                        )
                    },
                    timeout=30,
                ).raise_for_status()
            except Exception as e:
                logger.error(
                    f"Fallo al subir {block['block_id']} a {target_url}: {e}"
                )
                updated_blocks.append(block)
                continue

            new_replicas = [
                target_url if r == dead_url else r for r in replicas
            ]
            updated_block = {**block, "replicas": new_replicas}
            updated_blocks.append(updated_block)
            file_changed = True
            logger.info(
                f"Re-replicado {block['block_id']}: {dead_url} -> {target_url} "
                f"(fuente: {source_url})"
            )

        if file_changed:
            files_collection.update_one(
                {"_id": file_doc["_id"]},
                {"$set": {"blocks": updated_blocks}},
            )


def monitor_datanodes_loop() -> None:
    """Marca nodos sin heartbeat y dispara re-replicación."""
    while True:
        try:
            threshold = utc_now() - timedelta(seconds=HEARTBEAT_TIMEOUT_SEC)
            stale_nodes = list(datanodes_collection.find({
                "status": "alive",
                "last_seen": {"$lt": threshold},
            }))

            for node in stale_nodes:
                node_id = node["node_id"]
                dead_url = node["url"]
                datanodes_collection.update_one(
                    {"node_id": node_id},
                    {"$set": {"status": "dead"}},
                )
                logger.warning(
                    f"DataNode {node_id} sin heartbeat >{HEARTBEAT_TIMEOUT_SEC}s — marcado dead"
                )
                rereplicate_blocks_on_dead_node(dead_url)
        except Exception as e:
            logger.exception(f"Error en monitor de DataNodes: {e}")

        time.sleep(MONITOR_INTERVAL_SEC)


def start_datanode_monitor() -> None:
    thread = threading.Thread(target=monitor_datanodes_loop, daemon=True)
    thread.start()
    logger.info(
        f"Monitor de DataNodes iniciado (timeout={HEARTBEAT_TIMEOUT_SEC}s, "
        f"intervalo={MONITOR_INTERVAL_SEC}s)"
    )

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DFS NameNode",
    version="2.0.0",
    description="Nodo central de metadatos para el Sistema de Archivos Distribuido"
)


@app.on_event("startup")
def on_startup():
    start_datanode_monitor()


# ---------------------------------------------------------------------------
# Modelos de request
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    username: str
    password: str


class DirectoryRequest(BaseModel):
    path: str


# ===========================================================================
# HEALTH CHECK
# ===========================================================================

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "DFS NameNode",
        "status": "running",
        "datanodes_internal": DATANODES_INTERNAL,
        "datanodes_public":   DATANODES_PUBLIC
    }


# ===========================================================================
# AUTENTICACIÓN
# ===========================================================================

@app.post("/auth/register", tags=["Auth"])
def register(user: UserRegister):
    """Registra un nuevo usuario en el sistema."""
    existing = users_collection.find_one({"username": user.username})

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = hash_password(user.password)
    users_collection.insert_one({
        "username": user.username,
        "password": hashed
    })

    logger.info(f"Usuario registrado: {user.username}")
    return {"message": "User created"}


@app.post("/auth/login", tags=["Auth"])
def login(user: UserRegister):
    """Autentica un usuario y devuelve un token JWT."""
    existing = users_collection.find_one({"username": user.username})

    if not existing or not verify_password(user.password, existing["password"]):
        logger.warning(f"Intento de login fallido para: {user.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.username)
    logger.info(f"Login exitoso: {user.username}")
    return {"token": token}


# ===========================================================================
# GESTIÓN DE ARCHIVOS
# ===========================================================================

@app.get("/files/allocate/{filename}/{num_blocks}", tags=["Files"])
def allocate_file(
    filename: str,
    num_blocks: int,
    username: str = Depends(verify_token)
):
    """
    Asigna bloques a DataNodes usando Round-Robin con factor de replicación 2.
    Requiere autenticación.
    """
    datanodes = get_allocation_datanodes()
    if len(datanodes) < 2:
        raise HTTPException(
            status_code=503,
            detail="Se requieren al menos 2 DataNodes activos para replicar",
        )

    blocks = []
    total_nodes = len(datanodes)

    for i in range(num_blocks):
        block_id = f"{username}_{filename}_block{i}"
        primary = datanodes[i % total_nodes]
        replica = datanodes[(i + 1) % total_nodes]
        blocks.append({
            "block_id": block_id,
            "replicas": [primary, replica]
        })

    logger.info(f"Allocate: usuario={username} archivo={filename} bloques={num_blocks}")
    return {"filename": filename, "blocks": blocks}


@app.post("/files/register", tags=["Files"])
def register_file(
    file: FileMetadata,
    username: str = Depends(verify_token)
):
    """
    Registra la metadata de un archivo subido. Requiere autenticación.
    No permite duplicados del mismo usuario.
    """
    existing = files_collection.find_one({
        "filename": file.filename,
        "owner": username
    })
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"File '{file.filename}' already exists for user '{username}'. Use rm first."
        )

    files_collection.insert_one({
        "filename": file.filename,
        "owner": username,
        "total_size": file.total_size,
        "blocks": [
            {
                "block_id": b.block_id,
                "replicas": b.replicas,
                "checksum": b.checksum,
                "size_bytes": b.size_bytes
            }
            for b in file.blocks
        ]
    })

    logger.info(f"Archivo registrado: {file.filename} por {username} ({len(file.blocks)} bloques)")
    return {"message": "File registered"}


@app.get("/files", tags=["Files"])
def list_files(username: str = Depends(verify_token)):
    """Lista todos los archivos del usuario autenticado (ls)."""
    files = files_collection.find({"owner": username}, {"_id": 0, "filename": 1, "total_size": 1})
    result = [
        {
            "filename": f["filename"],
            "total_size": f.get("total_size")
        }
        for f in files
    ]
    logger.info(f"ls: usuario={username} ({len(result)} archivos)")
    return {"files": result}


@app.get("/files/{filename}", tags=["Files"])
def get_file(
    filename: str,
    username: str = Depends(verify_token)
):
    """Obtiene la metadata de un archivo del usuario autenticado."""
    file = files_collection.find_one({
        "filename": filename,
        "owner": username
    })

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "filename": file["filename"],
        "owner": file["owner"],
        "total_size": file.get("total_size"),
        "blocks": file["blocks"]
    }


@app.delete("/files/{filename}", tags=["Files"])
def delete_file(
    filename: str,
    username: str = Depends(verify_token)
):
    """
    Elimina un archivo: borra los bloques de todos los DataNodes
    y luego elimina la metadata del NameNode (rm).
    """
    file = files_collection.find_one({
        "filename": filename,
        "owner": username
    })

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    errors = []
    for block in file["blocks"]:
        for replica_url in block["replicas"]:
            try:
                resp = requests.delete(
                    f"{internal_url(replica_url)}/block/{block['block_id']}",
                    timeout=5
                )
                if resp.status_code not in (200, 404):
                    errors.append(f"{replica_url}/block/{block['block_id']}: {resp.status_code}")
            except Exception as e:
                errors.append(f"{replica_url}: {str(e)}")

    files_collection.delete_one({"filename": filename, "owner": username})

    logger.info(f"rm: archivo={filename} eliminado por {username}")
    if errors:
        logger.warning(f"rm: errores al eliminar bloques: {errors}")

    return {
        "message": f"File '{filename}' deleted",
        "block_errors": errors if errors else None
    }


# ===========================================================================
# GESTIÓN DE DIRECTORIOS
# ===========================================================================

@app.post("/directories", tags=["Directories"])
def create_directory(
    body: DirectoryRequest,
    username: str = Depends(verify_token)
):
    """Crea un directorio virtual (mkdir)."""
    existing = directories_collection.find_one({
        "path": body.path,
        "owner": username
    })
    if existing:
        raise HTTPException(status_code=409, detail=f"Directory '{body.path}' already exists")

    directories_collection.insert_one({
        "path": body.path,
        "owner": username
    })

    logger.info(f"mkdir: {body.path} por {username}")
    return {"message": f"Directory '{body.path}' created"}


@app.get("/directories", tags=["Directories"])
def list_directories(username: str = Depends(verify_token)):
    """Lista los directorios del usuario autenticado."""
    dirs = directories_collection.find({"owner": username}, {"_id": 0, "path": 1})
    return {"directories": [d["path"] for d in dirs]}


@app.delete("/directories/{path:path}", tags=["Directories"])
def remove_directory(
    path: str,
    username: str = Depends(verify_token)
):
    """
    Elimina un directorio y todos los archivos que contiene (rmdir).
    Un directorio no puede eliminarse si tiene archivos y no se usa force.
    """
    directory = directories_collection.find_one({
        "path": path,
        "owner": username
    })
    if not directory:
        raise HTTPException(status_code=404, detail=f"Directory '{path}' not found")

    # Eliminar archivos dentro del directorio
    prefix = path.rstrip("/") + "/"
    files_in_dir = list(files_collection.find({
        "owner": username,
        "filename": {"$regex": f"^{prefix}"}
    }))

    deleted_files = []
    for file in files_in_dir:
        for block in file["blocks"]:
            for replica_url in block["replicas"]:
                try:
                    requests.delete(
                        f"{internal_url(replica_url)}/block/{block['block_id']}",
                        timeout=5
                    )
                except Exception:
                    pass
        files_collection.delete_one({"_id": file["_id"]})
        deleted_files.append(file["filename"])

    directories_collection.delete_one({"path": path, "owner": username})

    logger.info(f"rmdir: {path} por {username} ({len(deleted_files)} archivos eliminados)")
    return {
        "message": f"Directory '{path}' removed",
        "deleted_files": deleted_files
    }


# ===========================================================================
# GESTIÓN DE DATANODES (heartbeat, registro, tolerancia a fallos)
# ===========================================================================

@app.post("/datanodes/register", tags=["DataNodes"])
def register_datanode(body: DataNodeRegister):
    """Registra o actualiza un DataNode en el catálogo del NameNode."""
    now = utc_now()
    datanodes_collection.update_one(
        {"node_id": body.node_id},
        {
            "$set": {
                "node_id": body.node_id,
                "url": body.url,
                "last_seen": now,
                "status": "alive",
            },
            "$setOnInsert": {"blocks": []},
        },
        upsert=True,
    )
    logger.info(f"DataNode registrado: {body.node_id} ({body.url})")
    return {"message": "DataNode registered", "node_id": body.node_id}


@app.post("/datanodes/heartbeat", tags=["DataNodes"])
def datanode_heartbeat(body: DataNodeHeartbeat):
    """Actualiza last_seen y opcionalmente la lista de bloques del DataNode."""
    node = datanodes_collection.find_one({"node_id": body.node_id})
    if not node:
        raise HTTPException(
            status_code=404,
            detail=f"DataNode '{body.node_id}' not registered. Call /datanodes/register first.",
        )

    update_fields = {
        "last_seen": utc_now(),
        "status": "alive",
    }
    if body.blocks is not None:
        update_fields["blocks"] = body.blocks

    datanodes_collection.update_one(
        {"node_id": body.node_id},
        {"$set": update_fields},
    )
    logger.debug(f"Heartbeat: {body.node_id}")
    return {"status": "ok", "node_id": body.node_id}


@app.get("/datanodes", tags=["DataNodes"])
def list_datanodes():
    """Lista todos los DataNodes registrados y su estado."""
    nodes = datanodes_collection.find({}, {"_id": 0})
    return {"datanodes": [serialize_datanode(n) for n in nodes]}
