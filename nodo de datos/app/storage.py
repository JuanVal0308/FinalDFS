import os

BLOCKS_DIR = "blocks"

os.makedirs(BLOCKS_DIR, exist_ok=True)

def save_block(block_id: str, data: bytes):

    path = f"{BLOCKS_DIR}/{block_id}"

    with open(path, "wb") as f:
        f.write(data)

def read_block(block_id: str):

    path = f"{BLOCKS_DIR}/{block_id}"

    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        return f.read()
