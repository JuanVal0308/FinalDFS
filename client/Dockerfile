FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV NAMENODE_URL=http://52.23.74.126:8000
ENV DFS_BLOCK_SIZE=67108864

ENTRYPOINT ["python", "dfs_cli.py"]
