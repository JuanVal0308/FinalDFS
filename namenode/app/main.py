import os
import logging
import requests

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel

from app.database import users_collection, files_collection, directories_collection
from app.models import FileMetadata
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

# URLs internas Docker — para comunicación contenedor-a-contenedor (heartbeat, re-replicación)
_raw_internal = os.getenv(
    "DATANODES",
    "http://localhost:8001,http://localhost:8002,http://localhost:8003"
)
DATANODES_INTERNAL = [url.strip() for url in _raw_internal.split(",")]

# URLs públicas — devueltas al cliente en /allocate para que pueda subir/bajar bloques.
# En local:  PUBLIC_IP=localhost  →  http://localhost:8001 ...
# En EC2:    PUBLIC_IP=<ip-publica> →  http://52.x.x.x:8001 ...
# Si PUBLIC_DATANODES no está definida, cae en los mismos valores que DATANODES (compatibilidad).
_raw_public = os.getenv("PUBLIC_DATANODES", _raw_internal)
DATANODES_PUBLIC = [url.strip() for url in _raw_public.split(",")]

logger.info(f"DataNodes internos : {DATANODES_INTERNAL}")
logger.info(f"DataNodes públicos : {DATANODES_PUBLIC}")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DFS NameNode",
    version="2.0.0",
    description="Nodo central de metadatos para el Sistema de Archivos Distribuido"
)


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
    blocks = []
    total_nodes = len(DATANODES_PUBLIC)

    for i in range(num_blocks):
        block_id = f"{username}_{filename}_block{i}"
        primary = DATANODES_PUBLIC[i % total_nodes]
        replica = DATANODES_PUBLIC[(i + 1) % total_nodes]
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
                    f"{replica_url}/block/{block['block_id']}",
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
                        f"{replica_url}/block/{block['block_id']}",
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
