# 📋 CONTEXT.md — FinalDFS: Sistema de Archivos Distribuido

> Documento de contexto técnico completo del proyecto.  
> Universidad Pontificia Bolivariana (UPB) — Sistemas Distribuidos  
> Última actualización: 2026-05-25

---

## 1. Visión General

**FinalDFS** es un Sistema de Archivos Distribuido (DFS) construido desde cero con Python. Simula el comportamiento básico de sistemas como HDFS (Hadoop Distributed File System): divide archivos en bloques, los replica en múltiples nodos de datos y centraliza la metadata en un nodo de nombres.

| Aspecto          | Descripción                                                  |
|------------------|--------------------------------------------------------------|
| Lenguaje         | Python 3.11                                                  |
| Framework API    | FastAPI + Uvicorn                                            |
| Base de datos    | MongoDB Atlas (vía PyMongo)                                  |
| Autenticación    | JWT (PyJWT) + bcrypt                                         |
| Contenedores     | Docker + Docker Compose                                      |
| Despliegue       | AWS EC2 (`52.23.74.126`)                                     |
| Tamaño de bloque | 1 MB                                                         |
| Replicación      | Factor 2 — algoritmo Round-Robin                             |

---

## 2. Arquitectura del Sistema

```
┌──────────────┐         ┌─────────────────────────────────────────┐
│              │ ──────▶ │              NameNode :8000              │
│   Cliente    │         │   FastAPI · MongoDB · JWT · bcrypt       │
│  (Python)    │         │   Metadata + Auth + Asignación bloques   │
│              │         └─────────────────────────────────────────┘
└──────┬───────┘
       │  Sube/descarga bloques directamente a los DataNodes
       ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  DataNode 1 │    │  DataNode 2 │    │  DataNode 3 │
│   :8001     │    │   :8002     │    │   :8003     │
│  FastAPI    │    │  FastAPI    │    │  FastAPI    │
│  /blocks    │    │  /blocks    │    │  /blocks    │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Responsabilidades por componente

| Componente   | Puerto | Rol                                                       |
|--------------|--------|-----------------------------------------------------------|
| **NameNode** | 8000   | Registra usuarios, emite JWT, asigna bloques, guarda metadata en MongoDB |
| **DataNode1**| 8001   | Almacena bloques en disco (`./blocks/`) y los sirve por HTTP |
| **DataNode2**| 8002   | Ídem DataNode1 (mismo contenedor, distinto puerto externo) |
| **DataNode3**| 8003   | Ídem DataNode1                                            |
| **Client**   | —      | Scripts Python para subir (`dfs_client.py`) y descargar (`dfs_get.py`) archivos |

---

## 3. Estructura de Archivos

```
FinalDFS/
│
├── docker-compose.yml              # Orquestación de todos los servicios
│
├── namenode/
│   ├── Dockerfile                  # Imagen Python 3.11, expone :8000
│   ├── requirements.txt            # fastapi, uvicorn, pymongo, pyjwt, bcrypt, python-dotenv
│   └── app/
│       ├── main.py                 # Endpoints REST del NameNode
│       ├── models.py               # Modelos Pydantic: FileMetadata, BlockMetadata
│       ├── database.py             # Conexión a MongoDB Atlas
│       └── auth.py                 # Funciones JWT + bcrypt
│
├── nodo de datos/                  # Plantilla del DataNode (Dockerfile.txt = Dockerfile)
│   ├── Dockerfile.txt              # ⚠️  Extensión incorrecta — renombrar a Dockerfile
│   ├── requirements.txt            # fastapi, uvicorn, python-multipart, requests
│   └── app/
│       ├── main.py                 # Endpoints: upload y get de bloques
│       └── storage.py              # I/O de bloques en disco (carpeta blocks/)
│
├── client/
│   ├── Dockerfile                  # Imagen del cliente (uso opcional)
│   ├── requirements.txt            # requests
│   ├── dfs_client.py               # Script de SUBIDA de archivos
│   └── dfs_get.py                  # Script de DESCARGA de archivos
│
├── docs/
│   ├── CONTEXT.md                  # ← Este archivo
│   └── Proyecto-dfs-v2.docx        # Documento de entrega académica
│
├── README.md                       # Documentación general del proyecto
├── archivo1.txt                    # Archivo de prueba 1
├── archivo2.txt                    # Archivo de prueba 2
├── bigfile.bin                     # Archivo binario de prueba (>1 MB)
├── replicated.bin                  # Archivo binario replicado de prueba
└── test.txt                        # Archivo de prueba rápida
```

---

## 4. Flujo de Operaciones

### 4.1 Subida de un archivo (`dfs_client.py`)

```
Cliente                          NameNode                      DataNodes
   │                                │                               │
   │─── GET /files/allocate/{n} ──▶ │                               │
   │◀── {blocks: [{id, replicas}]} ─│                               │
   │                                │                               │
   │  Para cada bloque:             │                               │
   │──────────────── POST /block/upload/{block_id} ───────────────▶ │
   │                                │   (a cada réplica asignada)   │
   │                                │                               │
   │─── POST /files/register ──────▶│                               │
   │◀── {message: "File registered"}│                               │
```

**Detalle del algoritmo:**
1. Lee el archivo completo en memoria.
2. Calcula `num_blocks = ceil(file_size / 1 MB)`.
3. Llama a `GET /files/allocate/{filename}/{num_blocks}` — el NameNode devuelve la asignación Round-Robin.
4. Por cada bloque, escribe un archivo temporal y lo sube vía `multipart/form-data` a **cada una de las 2 réplicas**.
5. Al terminar, registra la metadata completa en el NameNode (`POST /files/register`).

### 4.2 Descarga de un archivo (`dfs_get.py`)

```
Cliente                          NameNode                      DataNodes
   │                                │                               │
   │─── GET /files/{filename} ─────▶│                               │
   │◀── {filename, blocks} ─────────│                               │
   │                                │                               │
   │  Para cada bloque:             │                               │
   │──────────────── GET /block/{block_id} ──────────────────────▶  │
   │                 (intenta réplicas en orden, timeout 3s)        │
   │◀── bytes ──────────────────────────────────────────────────── │
   │  (concatena bloques → archivo final: downloaded_{filename})   │
```

**Tolerancia a fallos:** si una réplica no responde (timeout o error), el cliente intenta la siguiente. Si todas fallan, lanza excepción.

### 4.3 Estrategia de replicación Round-Robin

```
Bloque i → réplica primaria:   DATANODES[ i % 3 ]
            réplica secundaria: DATANODES[ (i+1) % 3 ]

Ejemplo con archivo de 3 bloques:
  Bloque 0 → DN1 (primario), DN2 (réplica)
  Bloque 1 → DN2 (primario), DN3 (réplica)
  Bloque 2 → DN3 (primario), DN1 (réplica)
```

---

## 5. API Reference

### 5.1 NameNode — `http://52.23.74.126:8000`

| Método | Endpoint                              | Body / Params                        | Respuesta                            |
|--------|---------------------------------------|--------------------------------------|--------------------------------------|
| GET    | `/`                                   | —                                    | `{service, status}`                  |
| POST   | `/auth/register`                      | `{username, password}`               | `{message: "User created"}`          |
| POST   | `/auth/login`                         | `{username, password}`               | `{token: "<JWT>"}`                   |
| GET    | `/files/allocate/{filename}/{n}`      | Path params                          | `{filename, blocks: [{block_id, replicas}]}` |
| POST   | `/files/register`                     | `FileMetadata` JSON                  | `{message: "File registered"}`       |
| GET    | `/files/{filename}`                   | Path param                           | `{filename, blocks}`                 |

### 5.2 DataNode — `http://52.23.74.126:800{1,2,3}`

| Método | Endpoint                    | Body                    | Respuesta                      |
|--------|-----------------------------|-------------------------|--------------------------------|
| GET    | `/`                         | —                       | `{service, status}`            |
| POST   | `/block/upload/{block_id}`  | `multipart/form-data`   | `{message, block_id}`          |
| GET    | `/block/{block_id}`         | —                       | Bytes (`application/octet-stream`) |

---

## 6. Modelos de Datos

### Pydantic (NameNode)

```python
class BlockMetadata(BaseModel):
    block_id: str        # e.g. "archivo1.txt_block0"
    replicas: List[str]  # e.g. ["http://....:8001", "http://....:8002"]

class FileMetadata(BaseModel):
    filename: str
    blocks: List[BlockMetadata]
```

### MongoDB (`dfs_system`)

**Colección `users`:**
```json
{
  "_id": ObjectId,
  "username": "juan",
  "password": "<bcrypt_hash>"
}
```

**Colección `files`:**
```json
{
  "_id": ObjectId,
  "filename": "archivo1.txt",
  "blocks": [
    { "block_id": "archivo1.txt_block0", "replicas": ["http://...:8001", "http://...:8002"] },
    { "block_id": "archivo1.txt_block1", "replicas": ["http://...:8002", "http://...:8003"] }
  ]
}
```

---

## 7. Autenticación

| Componente     | Biblioteca | Descripción                                      |
|----------------|------------|--------------------------------------------------|
| Hash contraseña| `bcrypt`   | `bcrypt.hashpw` con salt aleatorio               |
| Verificación   | `bcrypt`   | `bcrypt.checkpw`                                 |
| Token sesión   | `PyJWT`    | HS256, payload `{"username": "..."}`, sin expiración configurada |
| Secreto JWT    | `.env`     | Variable `JWT_SECRET` en `namenode/.env`         |

> ⚠️ **Limitación:** los endpoints de archivos (`/files/*`) **no validan el token JWT** — cualquier cliente sin autenticar puede acceder a ellos en la implementación actual.

---

## 8. Configuración y Variables de Entorno

### `namenode/.env` (no incluido en el repo)

```env
MONGO_URI=mongodb+srv://<usuario>:<contraseña>@<cluster>.mongodb.net/dfs_system
JWT_SECRET=<clave_secreta>
```

### URLs hardcodeadas (a revisar)

| Archivo                        | Variable         | Valor actual            |
|--------------------------------|------------------|-------------------------|
| `namenode/app/main.py`         | `DATANODES`      | `http://52.23.74.126:800{1,2,3}` |
| `client/dfs_client.py`         | `NAMENODE_URL`   | `http://52.23.74.126:8000` |
| `client/dfs_get.py`            | `NAMENODE_URL`   | `http://52.23.74.126:8000` |

> Estas IPs corresponden a una instancia AWS EC2. Para entornos locales o Docker Compose usar `http://namenode:8000` / `http://datanode{1,2,3}:8001`.

---

## 9. Despliegue con Docker Compose

```yaml
# docker-compose.yml (resumen)
services:
  namenode:    build: ./namenode    ports: 8000:8000
  datanode1:   build: ./datanode    ports: 8001:8001
  datanode2:   build: ./datanode    ports: 8002:8001
  datanode3:   build: ./datanode    ports: 8003:8001
```

> ⚠️ El `build` de los DataNodes apunta a `./datanode`, pero el directorio en el repo se llama `nodo de datos` (con espacio). Esto puede causar error en `docker-compose up --build`. Verificar que el directorio de build coincida.

### Comandos útiles

```bash
# Levantar todos los servicios
docker-compose up --build

# Ver logs en tiempo real
docker-compose logs -f

# Detener y limpiar
docker-compose down

# Subir un archivo (desde el host)
python client/dfs_client.py archivo1.txt

# Descargar un archivo
python client/dfs_get.py archivo1.txt
```

---

## 10. Limitaciones Conocidas y Mejoras Sugeridas

| # | Limitación                                              | Mejora sugerida                                   |
|---|---------------------------------------------------------|---------------------------------------------------|
| 1 | JWT no validado en endpoints de archivos                | Añadir `Depends(verify_token)` en FastAPI         |
| 2 | IPs hardcodeadas en cliente y NameNode                  | Usar variables de entorno (`NAMENODE_URL`, `DATANODE_URLS`) |
| 3 | `Dockerfile.txt` del DataNode (extensión incorrecta)    | Renombrar a `Dockerfile`                          |
| 4 | Directorio con espacio (`nodo de datos`)                | Renombrar a `datanode`                            |
| 5 | Sin expiración en tokens JWT                            | Añadir claim `exp` al payload                    |
| 6 | Sin heartbeat entre DataNodes y NameNode                | Implementar endpoint `/health` y polling periódico|
| 7 | Los archivos temporales se crean en `/tmp/` (Linux only)| Usar `tempfile` de Python para portabilidad       |
| 8 | No hay manejo de archivos duplicados                    | Verificar existencia antes de registrar en MongoDB|
| 9 | Sin paginación en listado de archivos                   | Implementar `GET /files` con paginación           |
| 10| Sin cifrado en tránsito                                 | Añadir TLS/HTTPS en producción                   |

---

## 11. Tecnologías y Dependencias

| Componente    | Paquete           | Uso                                      |
|---------------|-------------------|------------------------------------------|
| NameNode      | `fastapi`         | Framework REST                           |
| NameNode      | `uvicorn`         | Servidor ASGI                            |
| NameNode      | `pymongo`         | Driver MongoDB                           |
| NameNode      | `python-dotenv`   | Carga de variables de entorno            |
| NameNode      | `bcrypt`          | Hash de contraseñas                      |
| NameNode      | `pyjwt`           | Generación y validación JWT              |
| DataNode      | `fastapi`         | Framework REST                           |
| DataNode      | `uvicorn`         | Servidor ASGI                            |
| DataNode      | `python-multipart`| Recepción de archivos multipart          |
| Cliente       | `requests`        | Llamadas HTTP al NameNode y DataNodes    |

---

## 12. Equipo y Contexto Académico

- **Materia:** Sistemas Distribuidos  
- **Universidad:** Pontificia Bolivariana (UPB)  
- **Repositorio:** `JuanVal0308/feature/dfs-client` (rama de feature fusionada a `main`)  
- **Colaboradores:** Jose_Velezg, JuanVal0308  
