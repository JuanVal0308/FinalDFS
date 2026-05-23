# 📦 FinalDFS — Sistema de Archivos Distribuido

Sistema de archivos distribuido (DFS) implementado con Python, FastAPI y MongoDB. Permite subir archivos dividiéndolos en bloques replicados a través de múltiples nodos de datos, con un nodo de nombres central que gestiona la metadata y la autenticación de usuarios.

---

## 🏗️ Arquitectura

```
┌─────────────┐        ┌──────────────────────────────────────┐
│             │──────▶ │             NameNode :8000            │
│   Cliente   │        │  (Metadata + Auth + Allocación)       │
│             │        │          MongoDB                       │
└─────────────┘        └──────────────────────────────────────┘
       │
       │  Sube bloques directamente
       ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ DataNode 1  │   │ DataNode 2  │   │ DataNode 3  │
│   :8001     │   │   :8002     │   │   :8003     │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Componentes

| Componente | Tecnología | Puerto | Descripción |
|---|---|---|---|
| **NameNode** | FastAPI + MongoDB | `8000` | Gestiona metadata, autenticación y asignación de bloques |
| **DataNode 1** | FastAPI | `8001` | Almacena bloques de datos |
| **DataNode 2** | FastAPI | `8002` | Almacena bloques de datos |
| **DataNode 3** | FastAPI | `8003` | Almacena bloques de datos |
| **Client** | Python | — | Script para subir archivos al DFS |

---

## ⚙️ Funcionamiento

### Subida de un archivo

```
1. El cliente lee el archivo y lo divide en bloques de 1 MB
2. Solicita al NameNode la asignación de bloques (allocate)
3. El NameNode asigna 2 réplicas por bloque usando Round-Robin
4. El cliente sube cada bloque a sus réplicas asignadas
5. El cliente registra la metadata final en el NameNode
```

### Estrategia de replicación

Cada bloque se almacena en **2 réplicas** usando Round-Robin:

```
Bloque 0 → DataNode[0 % 3] = DN1  (réplica en DN2)
Bloque 1 → DataNode[1 % 3] = DN2  (réplica en DN3)
Bloque 2 → DataNode[2 % 3] = DN3  (réplica en DN1)
```

| Parámetro | Valor |
|---|---|
| Tamaño de bloque | 1 MB |
| Factor de replicación | 2 |
| Algoritmo de distribución | Round-Robin |

---

## 📁 Estructura del proyecto

```
FinalDFS/
├── docker-compose.yml
│
├── namenode/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py        # Endpoints REST: auth, allocate, register, get
│       ├── models.py      # Modelos Pydantic (FileMetadata, BlockMetadata)
│       ├── database.py    # Conexión MongoDB
│       └── auth.py        # JWT + bcrypt
│
├── nodo de datos/
│   ├── Dockerfile.txt
│   ├── requirements.txt
│   └── app/
│       ├── main.py        # Endpoints: upload block, get block
│       └── storage.py     # Lectura/escritura de bloques en disco
│
└── client/
    ├── Dockerfile
    ├── requirements.txt
    └── dfs_client.py      # Script de subida de archivos
```

---

## 🚀 Despliegue con Docker Compose

### Prerequisitos

- [Docker](https://www.docker.com/) y Docker Compose instalados
- Archivo `.env` en `namenode/` con las variables de entorno de MongoDB

### Variables de entorno (`namenode/.env`)

```env
MONGO_URI=mongodb+srv://<usuario>:<contraseña>@<cluster>.mongodb.net/<db>
```

### Levantar los servicios

```bash
docker-compose up --build
```

Esto levanta el NameNode y los 3 DataNodes. Verifica que estén corriendo:

```bash
curl http://localhost:8000   # NameNode
curl http://localhost:8001   # DataNode 1
curl http://localhost:8002   # DataNode 2
curl http://localhost:8003   # DataNode 3
```

---

## 📤 Uso del cliente

### Opción 1: Ejecutar directamente con Python

```bash
cd client
pip install -r requirements.txt
python dfs_client.py <ruta/al/archivo>
```

**Ejemplo:**

```bash
python dfs_client.py archivo1.txt
```

### Opción 2: Ejecutar con Docker

```bash
# Construir la imagen
docker build -t dfs-client ./client

# Ejecutar montando el archivo como volumen
docker run --rm -v "$(pwd)/archivo1.txt:/app/archivo1.txt" dfs-client archivo1.txt
```

> **Nota:** Si el NameNode corre en Docker Compose, reemplaza la IP en `dfs_client.py` por `http://namenode:8000` y añade `--network` al comando Docker Run.

---

## 🔌 API Reference

### NameNode (`http://localhost:8000`)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/auth/register` | Registrar usuario |
| `POST` | `/auth/login` | Login — devuelve JWT |
| `GET` | `/files/allocate/{filename}/{num_blocks}` | Asignar bloques en DataNodes |
| `POST` | `/files/register` | Registrar metadata de un archivo |
| `GET` | `/files/{filename}` | Obtener metadata de un archivo |

**Ejemplo — Registrar usuario:**

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "juan", "password": "1234"}'
```

**Ejemplo — Consultar metadata de archivo:**

```bash
curl http://localhost:8000/files/archivo1.txt
```

### DataNode (`http://localhost:8001`)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/block/upload/{block_id}` | Subir un bloque |
| `GET` | `/block/{block_id}` | Descargar un bloque |

---

## 🛠️ Tecnologías

| Capa | Tecnología |
|---|---|
| API | [FastAPI](https://fastapi.tiangolo.com/) |
| Base de datos | [MongoDB](https://www.mongodb.com/) (vía PyMongo) |
| Autenticación | JWT ([PyJWT](https://pyjwt.readthedocs.io/)) + [bcrypt](https://pypi.org/project/bcrypt/) |
| HTTP Client | [Requests](https://docs.python-requests.org/) |
| Contenedores | [Docker](https://www.docker.com/) + Docker Compose |
| Lenguaje | Python 3.11 |

---

## 👥 Autores

Proyecto desarrollado para la asignatura de **Sistemas Distribuidos** — Universidad Pontificia Bolivariana (UPB).
