import requests
import sys

NAMENODE_URL = "http://52.23.74.126:8000"

filename = sys.argv[1]

# obtener metadata
response = requests.get(
    f"{NAMENODE_URL}/files/{filename}"
)

metadata = response.json()

blocks = metadata["blocks"]

output_file = f"downloaded_{filename}"

with open(output_file, "wb") as outfile:

    for block in blocks:

        block_id = block["block_id"]

        replicas = block["replicas"]

        downloaded = False

        for replica_url in replicas:

            try:

                print(
                    f"Trying {block_id} from {replica_url}"
                )

                block_response = requests.get(
                    f"{replica_url}/block/{block_id}",
                    timeout=3
                )

                if block_response.status_code == 200:

                    outfile.write(
                        block_response.content
                    )

                    print(
                        f"Success from {replica_url}"
                    )

                    downloaded = True

                    break

            except Exception as e:

                print(
                    f"Replica failed: {replica_url}"
                )

        if not downloaded:

            raise Exception(
                f"All replicas failed for {block_id}"
            )

print(
    f"File reconstructed: {output_file}"
)