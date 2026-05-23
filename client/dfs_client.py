import math
import requests
import sys

BLOCK_SIZE = 1024 * 1024  # 1 MB

NAMENODE_URL = "http://52.23.74.126:8000"

filename = sys.argv[1]

# leer archivo completo
with open(filename, "rb") as f:

    data = f.read()

file_size = len(data)

# calcular cantidad bloques
num_blocks = math.ceil(
    file_size / BLOCK_SIZE
)

# pedir allocation al NameNode
response = requests.get(
    f"{NAMENODE_URL}/files/allocate/{filename}/{num_blocks}"
)

allocation = response.json()

blocks_metadata = []

# dividir archivo y subir bloques
for i in range(num_blocks):

    start = i * BLOCK_SIZE
    end = start + BLOCK_SIZE

    chunk = data[start:end]

    block_info = allocation["blocks"][i]

    block_id = block_info["block_id"]

    replicas = block_info["replicas"]

    # subir a cada réplica
    for replica_url in replicas:

        temp_block = f"/tmp/{block_id}"

        with open(temp_block, "wb") as f:
            f.write(chunk)

        with open(temp_block, "rb") as f:

            files = {
                "file": f
            }

            upload = requests.post(
                f"{replica_url}/block/upload/{block_id}",
                files=files
            )

        print(upload.json())

    # guardar metadata
    blocks_metadata.append({
        "block_id": block_id,
        "replicas": replicas
    })

# registrar metadata final
metadata = {
    "filename": filename,
    "blocks": blocks_metadata
}

register = requests.post(
    f"{NAMENODE_URL}/files/register",
    json=metadata
)

print(register.json())