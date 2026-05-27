# 📦 FinalDFS — Sistema de Archivos Distribuido

Sistema de archivos distribuido (DFS) implementado con Python, FastAPI y MongoDB Atlas. Divide archivos en bloques replicados en múltiples DataNodes, con un NameNode central para metadata, autenticación JWT y **tolerancia a fallos** (heartbeat, detección de nodos caídos y re-replicación).

| Entorno | NameNode | DataNodes |
|---------|----------|-----------|
| **Producción (EC2)** | http://52.23.74.126:8000 | :8001, :8002, :8003 |
| **Swagger** | http://52.23.74.126:8000/docs | — |

📚 **Más documentación:** [docs/README.md](docs/README.md) · [Guía EC2](docs/GUIA_EC2.md) · [Guía demo](docs/GUIA_DEMO.md) · [Informe](docs/INFORME.md)

---

## 🏗️ Arquitectura

```
┌──────────────┐        ┌──────────────────────────────────────────┐
│              │──────▶ │              NameNode :8000               │
│   Cliente    │        │  (Metadata + Auth + Asignación bloques)   │
│  (dfs_cli)   │        │           MongoDB Atlas                   │
│              │        └──────────────────────────────────────────┘
└──────┬───────┘
       │  Sube/descarga bloques directamente
       ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  DataNode 1 │   │  DataNode 2 │   │  DataNode 3 │
│   :8001     │   │   :8002     │   │   :8003     │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Componentes

| Componente | Tecnología | Puerto | Descripción |
|---|---|---|---|
| **NameNode** | FastAPI + MongoDB | `8000` | Gestiona metadata, autenticación JWT y asignación de bloques |
| **DataNode 1** | FastAPI | `8001` | Almacena bloques de datos en disco |
| **DataNode 2** | FastAPI | `8002` | Almacena bloques de datos en disco |
| **DataNode 3** | FastAPI | `8003` | Almacena bloques de datos en disco |
| **Client** | Python CLI | — | `dfs_cli.py` — interfaz unificada de línea de comandos |

---

## ⚙️ Funcionamiento

### Subida de un archivo (`put`)

```
1. El cliente divide el archivo en bloques (64 MB por defecto, configurable)
2. Calcula el checksum SHA-256 de cada bloque
3. Solicita al NameNode la asignación de bloques (allocate)
4. El NameNode asigna 2 réplicas por bloque usando Round-Robin
5. El cliente sube cada bloque a sus 2 réplicas directamente
6. El cliente registra la metadata completa en el NameNode
```

### Descarga de un archivo (`get`)

```
1. El cliente pide la metadata al NameNode (lista de bloques y réplicas)
2. Por cada bloque, intenta descargarlo de la primera réplica disponible
3. Verifica el checksum SHA-256 al recibir cada bloque
4. Si una réplica falla, intenta automáticamente la siguiente
5. Concatena los bloques en orden y reconstruye el archivo original
```

### Estrategia de replicación Round-Robin

Cada bloque se almacena en **2 réplicas**:

```
Bloque 0 → DN1 (primario)  +  DN2 (réplica)
Bloque 1 → DN2 (primario)  +  DN3 (réplica)
Bloque 2 → DN3 (primario)  +  DN1 (réplica)
```

| Parámetro | Valor |
|---|---|
| Tamaño de bloque | 64 MB (configurable via `DFS_BLOCK_SIZE`) |
| Factor de replicación | 2 |
| Algoritmo de distribución | Round-Robin |
| Integridad | SHA-256 por bloque |

### Tolerancia a fallos (Sprint 3)

```
DataNode arranca → POST /datanodes/register
Cada 30 s       → POST /datanodes/heartbeat
NameNode        → Si sin heartbeat > 90 s → status: dead
                 → Re-replica bloques huérfanos a nodos vivos
Cliente get     → Si una réplica falla, prueba la siguiente
```

Diagrama: [docs/diagrams/seq_heartbeat.md](docs/diagrams/seq_heartbeat.md)

---

## 📁 Estructura del proyecto

```
FinalDFS/
├── .env                    # IP pública del host (LOCAL: localhost / EC2: <ip>)
├── .env.example            # Plantilla de configuración
├── docker-compose.yml      # Orquestación de todos los servicios
│
├── docs/
│   ├── README.md           # Índice de documentación
│   ├── GUIA_EC2.md         # Despliegue en AWS
│   ├── GUIA_DEMO.md        # Guion de demostración
│   ├── INFORME.md          # Informe académico
│   ├── CONTEXT.md          # Contexto técnico
│   └── diagrams/           # Diagramas Mermaid (PUT, GET, heartbeat, AWS)
│
├── namenode/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example        # Plantilla MONGO_URI + JWT_SECRET
│   └── app/
│       ├── main.py         # Auth, archivos, directorios, datanodes, re-replicación
│       ├── models.py       # FileMetadata, BlockMetadata, DataNode*
│       ├── database.py     # users, files, directories, datanodes
│       └── auth.py         # JWT + bcrypt
│
├── datanode/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py         # Bloques + heartbeat hacia NameNode
│       └── storage.py      # I/O en disco (carpeta blocks/)
│
└── client/
    ├── Dockerfile
    ├── requirements.txt
    └── dfs_cli.py          # CLI: put, get, ls, status, rm, mkdir, rmdir
```

---

## 🚀 Despliegue

### Prerequisitos

- [Docker](https://www.docker.com/) y Docker Compose instalados
- Archivo `namenode/.env` con las credenciales de MongoDB y JWT

### 1. Crear `namenode/.env`

```bash
cp namenode/.env.example namenode/.env
# Editar con tus credenciales de MongoDB Atlas
```

```env
MONGO_URI=mongodb+srv://<usuario>:<contraseña>@<cluster>.mongodb.net/?retryWrites=true&w=majority
JWT_SECRET=<cadena-secreta-del-servidor>
```

> `JWT_SECRET` es la clave que firma los tokens (la defines tú). **No** es la contraseña del usuario ni el hash de MongoDB.

### 2. Configurar el entorno en `.env` (raíz del proyecto)

```env
# IP pública EC2 (NameNode :8000, DataNodes :8001-:8003)
PUBLIC_IP=52.23.74.126
```

### 3. Levantar los servicios

```bash
docker compose up -d --build
```

### 4. Verificar que todo está corriendo

```bash
curl http://52.23.74.126:8000   # NameNode
curl http://52.23.74.126:8001   # DataNode 1
curl http://52.23.74.126:8002   # DataNode 2
curl http://52.23.74.126:8003   # DataNode 3
curl http://52.23.74.126:8000/datanodes   # Estado de DataNodes
```

Respuesta esperada de cada servicio:
```json
{ "service": "DFS NameNode", "status": "running" }
{ "service": "DFS DataNode", "status": "running" }
```

### 5. Apagar los servicios

```bash
docker compose down
```

Guía detallada EC2: [docs/GUIA_EC2.md](docs/GUIA_EC2.md)

---

## 📤 Uso del cliente

### Instalación

```bash
cd client
pip install -r requirements.txt
```

### Variables de entorno del cliente (opcionales)

| Variable | Default | Descripción |
|---|---|---|
| `NAMENODE_URL` | `http://52.23.74.126:8000` | URL del NameNode |
| `DFS_BLOCK_SIZE` | `67108864` (64 MB) | Tamaño de bloque en bytes |

```bash
# Windows PowerShell
$env:NAMENODE_URL = "http://52.23.74.126:8000"

# Linux / Mac
export NAMENODE_URL=http://52.23.74.126:8000
```

---

### Flujo completo de uso

#### Paso 1 — Registrar usuario (solo la primera vez)

```bash
python dfs_cli.py register <usuario> <contraseña>
```

```
[OK] Usuario 'juan' registrado correctamente.
```

#### Paso 2 — Iniciar sesión

```bash
python dfs_cli.py login <usuario> <contraseña>
```

```
[OK] Sesión iniciada como 'juan'. Token guardado en .dfs_token
```

> El token se guarda automáticamente en `client/.dfs_token` y se usa en todos los comandos siguientes.

#### Paso 3 — Subir un archivo (`put`)

```bash
python dfs_cli.py put ruta/al/archivo.txt
```

```
[INFO] Archivo: archivo.txt (2097152 bytes) → 1 bloque(s) de 67108864 bytes
  Bloque 0: juan_archivo.txt_block0 (2097152 bytes, sha256=a1b2c3...)
    ✓ Réplica: http://localhost:8001
    ✓ Réplica: http://localhost:8002
[OK] Archivo 'archivo.txt' registrado en el DFS.
```

#### Paso 4 — Estado de DataNodes (`status`)

```bash
python dfs_cli.py status
```

```
Nodo         Estado    Bloques  Último heartbeat       URL
------------------------------------------------------------------------------------------
datanode1    ✓ alive         2  2026-05-26T...         http://52.23.74.126:8001
...
```

> No requiere login. Equivalente a `GET /datanodes`.

#### Paso 5 — Listar archivos (`ls`)

```bash
python dfs_cli.py ls
```

```
Archivo                                        Tamaño
------------------------------------------------------
archivo.txt                              2,097,152 bytes
reporte.pdf                              5,120,000 bytes
```

#### Paso 6 — Descargar un archivo (`get`)

```bash
python dfs_cli.py get archivo.txt
```

```
[INFO] Descargando 'archivo.txt' → 'downloaded_archivo.txt' (1 bloque(s))
  Intentando juan_archivo.txt_block0 desde http://localhost:8001 ...
    ✓ OK (2097152 bytes)
[OK] Archivo reconstruido: downloaded_archivo.txt
```

> El archivo se descarga como `downloaded_<nombre>` en el directorio actual.

#### Paso 7 — Eliminar un archivo (`rm`)

```bash
python dfs_cli.py rm archivo.txt
```

```
[OK] Archivo 'archivo.txt' eliminado del DFS.
```

> Elimina tanto la metadata en MongoDB como los bloques físicos en todos los DataNodes.

#### Gestión de directorios

```bash
# Crear un directorio virtual
python dfs_cli.py mkdir proyectos/2026

# Eliminar un directorio y todos sus archivos
python dfs_cli.py rmdir proyectos/2026
```

---

### Tabla de comandos

| Comando | Argumentos | Descripción |
|---|---|---|
| `register` | `<usuario> <contraseña>` | Crear cuenta nueva |
| `login` | `<usuario> <contraseña>` | Iniciar sesión (guarda token) |
| `put` | `<ruta_local>` | Subir archivo al DFS |
| `get` | `<nombre_remoto>` | Descargar archivo del DFS |
| `ls` | — | Listar mis archivos |
| `status` | — | Estado de los DataNodes (heartbeat) |
| `rm` | `<nombre_remoto>` | Eliminar archivo (metadata + bloques) |
| `mkdir` | `<ruta>` | Crear directorio virtual |
| `rmdir` | `<ruta>` | Eliminar directorio y su contenido |

---

## 🔌 API Reference

### NameNode (`http://52.23.74.126:8000`)

Documentación interactiva: http://52.23.74.126:8000/docs (Swagger UI).

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `GET` | `/` | No | Health check |
| `POST` | `/auth/register` | No | Registrar usuario |
| `POST` | `/auth/login` | No | Login — devuelve JWT |
| `GET` | `/files/allocate/{filename}/{n}` | ✅ JWT | Asignar bloques en DataNodes |
| `POST` | `/files/register` | ✅ JWT | Registrar metadata de un archivo |
| `GET` | `/files` | ✅ JWT | Listar archivos del usuario (`ls`) |
| `GET` | `/files/{filename}` | ✅ JWT | Obtener metadata de un archivo |
| `DELETE` | `/files/{filename}` | ✅ JWT | Eliminar archivo (`rm`) |
| `POST` | `/directories` | ✅ JWT | Crear directorio (`mkdir`) |
| `GET` | `/directories` | ✅ JWT | Listar directorios |
| `DELETE` | `/directories/{path}` | ✅ JWT | Eliminar directorio (`rmdir`) |
| `GET` | `/datanodes` | No | Estado de DataNodes (`status` en CLI) |
| `POST` | `/datanodes/register` | No | Registro de DataNode |
| `POST` | `/datanodes/heartbeat` | No | Heartbeat de DataNode |

> Todos los endpoints protegidos requieren el header: `Authorization: Bearer <token>`

### DataNode (`http://localhost:8001`)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Health check (incluye cantidad de bloques almacenados) |
| `POST` | `/block/upload/{block_id}` | Subir un bloque (`multipart/form-data`) |
| `GET` | `/block/{block_id}` | Descargar un bloque |
| `DELETE` | `/block/{block_id}` | Eliminar un bloque |
| `GET` | `/blocks` | Listar todos los bloques almacenados |

---

## 🛠️ Tecnologías

| Capa | Tecnología |
|---|---|
| API | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Base de datos | [MongoDB Atlas](https://www.mongodb.com/) vía PyMongo |
| Autenticación | JWT ([PyJWT](https://pyjwt.readthedocs.io/)) + [bcrypt](https://pypi.org/project/bcrypt/) |
| Integridad | SHA-256 (hashlib, stdlib) |
| HTTP Client | [Requests](https://docs.python-requests.org/) |
| Contenedores | [Docker](https://www.docker.com/) + Docker Compose |
| Lenguaje | Python 3.11 |

---

## 🔧 Solución de problemas

| Problema | Solución |
|----------|----------|
| `No hay sesión activa` | `python dfs_cli.py login usuario contraseña` |
| Login con hash largo (`JDJiJ...`) | Usar contraseña en texto plano del `register`, no el hash de MongoDB |
| `status` no reconocido | `git pull` y estar en `client/` |
| Nodos `dead` en `/datanodes` | `docker compose restart datanode1 datanode2 datanode3` |
| `put` falla en réplicas | `python dfs_cli.py status` — verificar nodos `alive` |
| Ver bloques de un archivo | `GET /files/{nombre}` con `Authorization: Bearer $(cat .dfs_token)` |

Más detalle: [docs/GUIA_EC2.md](docs/GUIA_EC2.md) · Demo de fallos: [docs/GUIA_DEMO.md](docs/GUIA_DEMO.md)

---

## 👥 Autores

Proyecto desarrollado para **Sistemas Distribuidos** — Universidad Pontificia Bolivariana (UPB).

**Equipo:** Jose_Velezg · JuanVal0308 · Sara
