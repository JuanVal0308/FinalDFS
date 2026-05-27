# Guía de demostración — FinalDFS

Guion para video, presentación o informe (§8). Usar **dos contextos**:

- **SSH (EC2):** Docker, `curl`, logs
- **Cliente:** `~/FinalDFS/client` → `python3 dfs_cli.py`

---

## Preparación (5 min)

```bash
# En EC2
cd ~/FinalDFS
docker compose ps
docker compose restart datanode1 datanode2 datanode3
sleep 10

cd client
python3 dfs_cli.py login juan 123   # o: register demo demo123 && login demo demo123
python3 dfs_cli.py status
```

Captura: 3 DataNodes `alive`.

---

## Parte 1 — Operación normal (10 min)

### 1.1 Subir archivo pequeño

```bash
cd ~/FinalDFS/client
python3 dfs_cli.py put ../archivo1.txt
python3 dfs_cli.py ls
```

### 1.2 Ver bloques en DataNodes

```bash
curl -s http://localhost:8001/blocks | python3 -m json.tool
curl -s http://localhost:8002/blocks | python3 -m json.tool
curl -s http://localhost:8003/blocks | python3 -m json.tool
```

Buscar `juan_archivo1.txt_block0` (o `demo_...` según usuario) en **2 nodos**.

### 1.3 Metadata en el NameNode

```bash
TOKEN=$(cat .dfs_token)
curl -s "http://localhost:8000/files/archivo1.txt" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### 1.4 Descargar y verificar

```bash
python3 dfs_cli.py get archivo1.txt
diff ../archivo1.txt downloaded_archivo1.txt && echo "OK"
```

---

## Parte 2 — Archivo grande (4 bloques de 64 MB)

```bash
cd ~/FinalDFS
dd if=/dev/zero of=Alvarito.bin bs=1M count=256 status=progress
ls -lh Alvarito.bin

cd client
python3 dfs_cli.py put ../Alvarito.bin
```

Ver 4 bloques en metadata:

```bash
TOKEN=$(cat .dfs_token)
curl -s "http://localhost:8000/files/Alvarito.bin" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Listar en cada DataNode y buscar `block0` … `block3`.

---

## Parte 3 — Tolerancia a fallos (15 min)

### 3.1 Simular caída

```bash
cd ~/FinalDFS
docker stop datanode1
docker compose ps
```

### 3.2 GET con failover (cliente sigue funcionando)

```bash
cd ~/FinalDFS/client
python3 dfs_cli.py get archivo1.txt
```

### 3.3 Detección (>90 s)

```bash
echo "Esperando 2 minutos..."
sleep 120
curl -s http://localhost:8000/datanodes | python3 -m json.tool
python3 dfs_cli.py status
```

`datanode1` debe estar `"status": "dead"`.

### 3.4 Re-replicación

```bash
cd ~/FinalDFS
docker compose logs namenode 2>&1 | grep -i replic | tail -15
```

### 3.5 Recuperación

```bash
docker start datanode1
docker compose restart datanode1
sleep 10
curl -s http://localhost:8000/datanodes | python3 -m json.tool
```

---

## Checklist de capturas

Ver [capturas/README.md](capturas/README.md).

---

## Navegador (opcional)

- Swagger: http://52.23.74.126:8000/docs
- Authorize con `Bearer <token>` desde `client/.dfs_token`
