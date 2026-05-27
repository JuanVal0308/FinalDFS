# CONTEXT.md — FinalDFS

> Contexto técnico del sistema.  
> UPB — Sistemas Distribuidos · Última actualización: 2026-05-26

---

## 1. Visión general

**FinalDFS** es un DFS en Python inspirado en HDFS: partición en bloques, replicación en DataNodes y metadata centralizada en un NameNode con MongoDB Atlas.

| Aspecto | Valor |
|---------|--------|
| Lenguaje | Python 3.11 |
| API | FastAPI + Uvicorn |
| Base de datos | MongoDB Atlas (`dfs_system`) |
| Autenticación | JWT (PyJWT) + bcrypt |
| Contenedores | Docker Compose |
| Despliegue | AWS EC2 `52.23.74.126` |
| Bloque por defecto | 64 MB (`DFS_BLOCK_SIZE`) |
| Replicación | Factor 2, Round-Robin |
| Integridad | SHA-256 por bloque |
| Tolerancia a fallos | Heartbeat, detección >90 s, re-replicación |

---

## 2. Arquitectura

```
Cliente (dfs_cli) ──► NameNode :8000 ──► MongoDB Atlas
       │
       └──► DataNode1 :8001
       └──► DataNode2 :8002
       └──► DataNode3 :8003
```

| Componente | Puerto | Rol |
|------------|--------|-----|
| NameNode | 8000 | Auth, metadata, allocate, monitor, re-replicación |
| DataNode 1–3 | 8001–8003 | Almacenamiento de bloques, heartbeat |
| Cliente | — | `dfs_cli.py` — orquestación put/get/ls/status |

Comunicación interna Docker: `namenode:8000`, `datanode1:8001`, etc.  
URLs públicas al cliente: `http://52.23.74.126:800x`.

---

## 3. Estructura del repositorio

```
FinalDFS/
├── docker-compose.yml
├── .env / .env.example          # PUBLIC_IP
├── namenode/                    # NameNode + namenode/.env (gitignored)
├── datanode/                    # DataNodes
├── client/                      # dfs_cli.py
└── docs/
    ├── README.md                # Índice
    ├── GUIA_EC2.md
    ├── GUIA_DEMO.md
    ├── INFORME.md
    ├── CONTEXT.md
    ├── TASK_MANAGEMENT.md
    └── diagrams/
```

Scripts legacy (opcionales): `dfs_client.py`, `dfs_get.py` — sustituidos por `dfs_cli.py`.

---

## 4. Flujos principales

### 4.1 PUT (`dfs_cli.py put`)

1. Login → JWT en `.dfs_token`
2. Divide archivo en bloques de 64 MB (configurable)
3. `GET /files/allocate/{file}/{n}` → asignación Round-Robin (2 réplicas)
4. `POST /block/upload/{block_id}` a cada réplica
5. `POST /files/register` con checksum SHA-256

Diagrama: [diagrams/seq_put.md](diagrams/seq_put.md)

### 4.2 GET (`dfs_cli.py get`)

1. `GET /files/{filename}` → bloques y réplicas
2. Por cada bloque, intenta réplicas en orden
3. Verifica checksum; concatena → `downloaded_{filename}`

Diagrama: [diagrams/seq_get.md](diagrams/seq_get.md)

### 4.3 Heartbeat y re-replicación

1. DataNode: `POST /datanodes/register` al arrancar
2. Cada 30 s: `POST /datanodes/heartbeat`
3. NameNode: monitor cada 30 s; sin señal >90 s → `dead`
4. Re-replica bloques desde réplica viva hacia otro nodo `alive`

Diagrama: [diagrams/seq_heartbeat.md](diagrams/seq_heartbeat.md)

### 4.4 Round-Robin (3 DataNodes, factor 2)

```
Bloque 0 → DN1 + DN2
Bloque 1 → DN2 + DN3
Bloque 2 → DN3 + DN1
Bloque 3 → DN1 + DN2  ...
```

---

## 5. API (resumen)

Ver tabla completa en [README.md](../README.md#-api-reference).

Endpoints clave Sprint 3:

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/datanodes` | Estado de nodos |
| POST | `/datanodes/register` | Registro DataNode |
| POST | `/datanodes/heartbeat` | Actualizar `last_seen` |

---

## 6. Modelos de datos

### MongoDB — colección `users`

```json
{ "username": "juan", "password": "<bcrypt_hash>" }
```

### MongoDB — colección `files`

```json
{
  "filename": "archivo1.txt",
  "owner": "juan",
  "total_size": 52,
  "blocks": [{
    "block_id": "juan_archivo1.txt_block0",
    "replicas": ["http://52.23.74.126:8001", "http://52.23.74.126:8002"],
    "checksum": "<sha256>",
    "size_bytes": 52
  }]
}
```

### MongoDB — colección `datanodes`

```json
{
  "node_id": "datanode1",
  "url": "http://52.23.74.126:8001",
  "status": "alive",
  "last_seen": "2026-05-26T12:00:00Z",
  "blocks": ["juan_archivo1.txt_block0"]
}
```

### MongoDB — colección `directories`

```json
{ "path": "proyectos/2026", "owner": "juan" }
```

---

## 7. Autenticación

| Concepto | Ubicación | Notas |
|----------|-----------|--------|
| `JWT_SECRET` | `namenode/.env` | Clave del servidor (tú la defines) |
| Token de sesión | Respuesta `/auth/login`, `client/.dfs_token` | Header `Authorization: Bearer ...` |
| Contraseña usuario | Texto plano en login; hash bcrypt en MongoDB | No usar el hash como contraseña |

Endpoints `/files/*` y `/directories/*` requieren JWT válido.

---

## 8. Variables de entorno

### Raíz (`.env`)

| Variable | Default EC2 | Uso |
|----------|-------------|-----|
| `PUBLIC_IP` | `52.23.74.126` | URLs públicas en allocate |

### `namenode/.env`

| Variable | Uso |
|----------|-----|
| `MONGO_URI` | MongoDB Atlas |
| `JWT_SECRET` | Firma JWT |

### NameNode (docker-compose)

| Variable | Default |
|----------|---------|
| `DATANODES` | URLs internas Docker |
| `PUBLIC_DATANODES` | URLs públicas EC2 |
| `HEARTBEAT_TIMEOUT_SEC` | 90 |
| `MONITOR_INTERVAL_SEC` | 30 |

### DataNode

| Variable | Default |
|----------|---------|
| `NODE_ID` | datanode1/2/3 |
| `NAMENODE_URL` | http://namenode:8000 |
| `NODE_PUBLIC_URL` | http://52.23.74.126:800x |
| `HEARTBEAT_INTERVAL_SEC` | 30 |

### Cliente

| Variable | Default |
|----------|---------|
| `NAMENODE_URL` | http://52.23.74.126:8000 |
| `DFS_BLOCK_SIZE` | 67108864 (64 MB) |

---

## 9. Despliegue

```bash
cp .env.example .env
cp namenode/.env.example namenode/.env
# editar namenode/.env
docker compose up -d --build
```

Guías: [GUIA_EC2.md](GUIA_EC2.md) · [GUIA_DEMO.md](GUIA_DEMO.md)

---

## 10. Limitaciones conocidas

| # | Limitación |
|---|------------|
| 1 | Tokens JWT sin expiración (`exp`) por defecto |
| 2 | Re-replicación vía NameNode (no copia directa entre DataNodes) |
| 3 | `put` carga el archivo completo en memoria del cliente |
| 4 | Sin TLS/HTTPS en el despliegue actual |
| 5 | Orden de arranque: si DataNodes suben antes que NameNode, reintentan registro |

---

## 11. Equipo

- **Materia:** Sistemas Distribuidos — UPB
- **Repositorio:** https://github.com/JuanVal0308/FinalDFS
- **Colaboradores:** Jose_Velezg, JuanVal0308, Sara
