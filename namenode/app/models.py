from pydantic import BaseModel
from typing import List, Optional


class BlockMetadata(BaseModel):
    block_id: str
    replicas: List[str]
    checksum: Optional[str] = None   # SHA-256 del bloque
    size_bytes: Optional[int] = None  # Tamaño real del bloque en bytes


class FileMetadata(BaseModel):
    filename: str
    blocks: List[BlockMetadata]
    owner: Optional[str] = None       # Usuario propietario del archivo
    total_size: Optional[int] = None  # Tamaño total del archivo en bytes


class DataNodeRegister(BaseModel):
    node_id: str
    url: str


class DataNodeHeartbeat(BaseModel):
    node_id: str
    blocks: Optional[List[str]] = None
