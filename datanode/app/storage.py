import os

BLOCKS_DIR = "blocks"

os.makedirs(BLOCKS_DIR, exist_ok=True)


def save_block(block_id: str, data: bytes) -> None:
    path = os.path.join(BLOCKS_DIR, block_id)
    with open(path, "wb") as f:
        f.write(data)


def read_block(block_id: str) -> bytes | None:
    path = os.path.join(BLOCKS_DIR, block_id)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def delete_block(block_id: str) -> bool:
    """Elimina un bloque del disco. Retorna True si existía, False si no."""
    path = os.path.join(BLOCKS_DIR, block_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def list_blocks() -> list[str]:
    """Retorna la lista de block_ids almacenados en este DataNode."""
    return os.listdir(BLOCKS_DIR)
