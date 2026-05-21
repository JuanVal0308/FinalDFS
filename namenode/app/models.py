from pydantic import BaseModel
from typing import List

class BlockMetadata(BaseModel):

    block_id: str
    replicas: List[str]

class FileMetadata(BaseModel):

    filename: str
    blocks: List[BlockMetadata]
