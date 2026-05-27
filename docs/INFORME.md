# Informe técnico — FinalDFS

> Sistema de Archivos Distribuido (DFS)  
> Universidad Pontificia Bolivariana — Sistemas Distribuidos  
> Equipo: Jose_Velezg, JuanVal0308, Sara  
> Despliegue: AWS EC2 `52.23.74.126`

**Documentación operativa:** [GUIA_EC2.md](GUIA_EC2.md) · [GUIA_DEMO.md](GUIA_DEMO.md) · [README del repo](../README.md)

---

## §1 Objetivo

Desarrollar un sistema de archivos distribuido que particione archivos en bloques, los replique en múltiples nodos de datos y centralice la metadata en un NameNode, ofreciendo operaciones tipo `put`, `get`, `ls`, `rm`, `mkdir` y `rmdir`, con autenticación JWT y tolerancia básica a fallos mediante heartbeat y re-replicación.

---

## §2 Marco teórico

Un DFS separa **metadata** (nombres, ubicación de bloques, réplicas) de **datos** (contenido de bloques). Modelos como HDFS usan un nodo maestro (NameNode) y varios trabajadores (DataNodes). La **replicación** aumenta disponibilidad: si un nodo falla, otra réplica sirve el bloque. El **heartbeat** permite detectar nodos caídos; la **re-replicación** restaura el factor de copias acordado.

---

## §3 Descripción del servicio

**FinalDFS** expone una API REST (FastAPI) y un cliente CLI (`dfs_cli.py`). El usuario se registra e inicia sesión; el NameNode emite un JWT. Al subir un archivo, el cliente solicita asignación de bloques, sube cada bloque a dos DataNodes y registra metadata en MongoDB Atlas. La descarga reconstruye el archivo desde las réplicas, con failover si una falla.

| Parámetro | Valor |
|-----------|--------|
| Tamaño de bloque por defecto | 64 MB (`DFS_BLOCK_SIZE`) |
| Factor de replicación | 2 |
| Base de datos | MongoDB Atlas (`dfs_system`) |

---

## §4 Arquitectura del sistema

```
Cliente ──HTTP──► NameNode (:8000) ──► MongoDB Atlas
   │
   └──HTTP──► DataNode1 (:8001), DataNode2 (:8002), DataNode3 (:8003)
```

- **NameNode:** autenticación, asignación Round-Robin, metadata, monitoreo de DataNodes, re-replicación.
- **DataNodes:** almacenamiento de bloques en disco, registro y heartbeat hacia el NameNode.
- **Cliente:** orquesta put/get y comandos de directorio; no almacena datos del DFS.

Diagramas: `docs/diagrams/deploy_aws.md`, `docs/CONTEXT.md`.

---

## §5 Protocolos y APIs

### NameNode (`http://52.23.74.126:8000`)

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Registro de usuario |
| POST | `/auth/login` | No | Login → JWT |
| GET | `/files/allocate/{file}/{n}` | JWT | Asignación de bloques |
| POST | `/files/register` | JWT | Registrar metadata |
| GET | `/files` | JWT | Listar archivos (`ls`) |
| GET | `/files/{filename}` | JWT | Metadata de un archivo |
| DELETE | `/files/{filename}` | JWT | Eliminar archivo (`rm`) |
| POST | `/directories` | JWT | `mkdir` |
| DELETE | `/directories/{path}` | JWT | `rmdir` |
| POST | `/datanodes/register` | No | Registro de DataNode |
| POST | `/datanodes/heartbeat` | No | Heartbeat |
| GET | `/datanodes` | No | Estado de nodos |

### DataNode (`:8001`–`:8003`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/block/upload/{block_id}` | Subir bloque |
| GET | `/block/{block_id}` | Descargar bloque |
| DELETE | `/block/{block_id}` | Eliminar bloque |
| GET | `/blocks` | Listar bloques locales |

Documentación interactiva: `/docs` (Swagger).

Diagramas de secuencia: `docs/diagrams/seq_put.md`, `seq_get.md`, `seq_heartbeat.md`.

---

## §6 Algoritmos

### 6.1 Distribución de bloques (Round-Robin)

Para un archivo con `n` bloques y `k` DataNodes activos:

- Bloque `i` → primario: `nodes[i % k]`
- Réplica: `nodes[(i + 1) % k]`

El NameNode devuelve URLs públicas (`http://52.23.74.126:800x`) al cliente; internamente usa hostnames Docker (`datanode1:8001`, etc.).

### 6.2 Registro y heartbeat

1. Al arrancar, cada DataNode ejecuta `POST /datanodes/register` con `node_id` y `url`.
2. Cada 30 s envía `POST /datanodes/heartbeat` con la lista de bloques locales.
3. El NameNode actualiza `last_seen` y `status: alive` en la colección `datanodes`.

### 6.3 Detección de fallos

Un hilo en el NameNode revisa cada 30 s los nodos con `last_seen` mayor a **90 s** y los marca `dead`.

### 6.4 Re-replicación activa

Cuando un nodo pasa a `dead`:

1. Se buscan archivos cuyos bloques listan la URL del nodo caído.
2. Se lee el bloque desde una réplica viva (HTTP interno).
3. Se sube a otro DataNode `alive` que no tenga ya esa réplica.
4. Se actualiza el array `replicas` en MongoDB.

### 6.5 Integridad (checksum)

En `put`, el cliente calcula SHA-256 por bloque y lo envía en `POST /files/register`. En `get`, se verifica contra el checksum almacenado.

---

## §7 Entorno de ejecución

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.11 |
| API | FastAPI + Uvicorn |
| BD | MongoDB Atlas (PyMongo) |
| Contenedores | Docker Compose |
| Nube | AWS EC2 Ubuntu, IP `52.23.74.126` |

**Despliegue:**

```bash
git clone https://github.com/JuanVal0308/FinalDFS.git
cd FinalDFS
cp .env.example .env
# Configurar namenode/.env (MONGO_URI, JWT_SECRET)
docker compose up -d --build
```

**Cliente:**

```bash
cd client
pip install -r requirements.txt
python dfs_cli.py login <usuario> <password>
python dfs_cli.py status
```

---

## §8 Pruebas y resultados

### 8.1 Pruebas funcionales

| Prueba | Comando | Resultado esperado |
|--------|---------|-------------------|
| Health NameNode | `curl http://52.23.74.126:8000/` | `status: running` |
| Estado nodos | `python dfs_cli.py status` | 3 nodos `alive` |
| Subida | `python dfs_cli.py put archivo1.txt` | Réplicas en 2 DataNodes |
| Listado | `python dfs_cli.py ls` | Archivo visible |
| Descarga | `python dfs_cli.py get archivo1.txt` | `downloaded_*` correcto |

### 8.2 Tolerancia a fallos

| Paso | Acción | Resultado |
|------|--------|-----------|
| 1 | `GET /datanodes` | Todos `alive` |
| 2 | `put` de archivo de prueba | Bloques en ≥2 nodos |
| 3 | `docker stop datanode1` | Puerto 8001 no responde |
| 4 | `get` del archivo | Descarga OK (failover) |
| 5 | Esperar >90 s | `datanode1` → `dead` en `/datanodes` |
| 6 | Logs NameNode | Mensaje de re-replicación |
| 7 | `docker start datanode1` + restart | Vuelve `alive` |

**Evidencia:** insertar capturas de pantalla en carpeta `docs/capturas/` (terminal `docker compose ps`, salida de `status`, `put`, `get`, `/datanodes` con nodo `dead`, logs de re-replicación).

### 8.3 Comando `status` (CLI)

```
python dfs_cli.py status
```

Muestra `node_id`, estado (`alive`/`dead`), cantidad de bloques, último heartbeat y URL pública de cada DataNode.

---

## §9 Conclusiones

Se implementó un DFS funcional con arquitectura maestro–trabajador, replicación factor 2, autenticación JWT, CLI completa y mecanismos de heartbeat, detección de nodos caídos y re-replicación. El despliegue en EC2 con Docker permite demostrar el sistema de forma reproducible.

**Limitaciones:** la re-replicación la ejecuta el NameNode (no hay canal directo DataNode–DataNode); los tokens JWT no expiran por defecto; el monitor depende de que los DataNodes reinicien el registro si el NameNode arranca después.

**Trabajo futuro:** expiración de JWT, reintento automático de registro en DataNodes, métricas Prometheus y cifrado TLS en producción.

---

## Referencias

- `README.md`, `docs/CONTEXT.md`, `docs/TASK_MANAGEMENT.md`
- Repositorio: https://github.com/JuanVal0308/FinalDFS
