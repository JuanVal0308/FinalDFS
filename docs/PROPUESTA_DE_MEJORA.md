# 📑 PROPUESTA DE MEJORA — FinalDFS

> **Documento de análisis de brechas y plan de acción**  
> Elaborado con base en `CONTEXT.md` y `Proyecto-dfs-v2.docx`  
> Universidad Pontificia Bolivariana (UPB) — Sistemas Distribuidos  
> Fecha: 2026-05-25

---

## Tabla de Contenidos

1. [Comparativa con el enunciado original](#1-comparativa-con-el-enunciado-original)
2. [Análisis frente a los criterios de evaluación](#2-análisis-frente-a-los-criterios-de-evaluación)
3. [Propuesta de mejoras y funcionalidades faltantes](#3-propuesta-de-mejoras-y-funcionalidades-faltantes)
4. [Plan de acción priorizado](#4-plan-de-acción-priorizado)

---

## 1. Comparativa con el Enunciado Original

### 1.1 Requisitos cumplidos totalmente

| # | Requisito del enunciado | Evidencia en el proyecto |
|---|-------------------------|--------------------------|
| R1 | Arquitectura Maestro–Trabajador (NameNode + DataNodes) | `docker-compose.yml` define `namenode` + `datanode1/2/3`; `CONTEXT.md §2` |
| R2 | NameNode central con tabla de metadatos | `namenode/app/main.py`, colección `files` en MongoDB; `CONTEXT.md §6` |
| R3 | Múltiples DataNodes que almacenan bloques | 3 DataNodes en FastAPI, cada uno con su directorio `blocks/`; `CONTEXT.md §3` |
| R4 | Operación `put` — dividir archivo en bloques y distribuirlos | `client/dfs_client.py` implementa la subida completa; `CONTEXT.md §4.1` |
| R5 | Operación `get` — recuperar archivo reconstruyéndolo | `client/dfs_get.py` implementa la descarga con failover; `CONTEXT.md §4.2` |
| R6 | Replicación mínima: cada bloque en al menos 2 DataNodes | Factor de replicación 2 con Round-Robin; `CONTEXT.md §4.3` |
| R7 | Autenticación básica usuario/contraseña | `POST /auth/register` y `/auth/login` con bcrypt + JWT; `CONTEXT.md §7` |
| R8 | Comunicación vía REST sobre HTTP | Todos los componentes usan FastAPI + `requests`; `CONTEXT.md §5` |
| R9 | Ejecución mediante contenedores Docker | `Dockerfile` en cada componente + `docker-compose.yml`; `CONTEXT.md §9` |
| R10 | Infraestructura en nube (AWS) | IPs de producción apuntan a `52.23.74.126` (EC2); `CONTEXT.md §8` |
| R11 | Cliente envía bloques directamente a DataNodes | `dfs_client.py` sube directamente sin intermediar el NameNode; `CONTEXT.md §4.1` |

### 1.2 Requisitos cumplidos parcialmente

| # | Requisito del enunciado | Estado actual | Brecha identificada |
|---|-------------------------|---------------|---------------------|
| P1 | Tamaño de bloque **configurable**, con valor por defecto de 64 MB | Implementado con 1 MB **hardcodeado** | No existe variable de entorno ni parámetro configurable; el valor por defecto no corresponde a los 64 MB establecidos |
| P2 | CLI funcional para todas las operaciones básicas | Solo `put` y `get` implementados | Faltan `ls`, `rm`, `mkdir`, `rmdir` según el enunciado |
| P3 | Gestión de metadatos en el NameNode | Registro y consulta funcionales | No hay actualización ni eliminación de metadata; no se verifica duplicidad de archivos |
| P4 | Autenticación aplicada a **todas** las operaciones | Registro e inicio de sesión funcionan | Los endpoints `/files/*` **no validan el token JWT** — cualquier cliente no autenticado puede operar; `CONTEXT.md §7` |
| P5 | Garantía de replicación **en todo momento** | Replicación en escritura inicial garantizada | El sistema no detecta ni reacciona ante la caída de un DataNode para re-replicar bloques huérfanos |
| P6 | Comunicación DataNode ↔ NameNode | Cliente → NameNode → respuesta de asignación implementada | No hay registro activo de DataNodes ni reporte de bloques desde los DataNodes hacia el NameNode (heartbeat) |

### 1.3 Requisitos no abordados o ausentes

| # | Requisito del enunciado | Estado |
|---|-------------------------|--------|
| A1 | **`ls`** — listar archivos del usuario autenticado | ❌ No implementado |
| A2 | **`rm`** — eliminar un archivo (bloques + metadata) | ❌ No implementado |
| A3 | **`mkdir` / `rmdir`** — gestión básica de directorios | ❌ No implementado |
| A4 | **Detección de caídas de DataNodes** — el sistema debe continuar operativo y registrar el evento | ❌ No implementado |
| A5 | **Replicación activa** — si un DataNode falla, garantizar que los bloques con solo 1 réplica sean replicados a otro nodo | ❌ No implementado |
| A6 | **Manejo de bloques faltantes o corruptos** — validación de integridad (checksum/hash) y respuesta ante errores | ❌ No implementado |
| A7 | **DataNode → NameNode: registro inicial y reporte periódico de bloques** | ❌ No implementado |
| A8 | **Logs del sistema** — trazabilidad de operaciones, errores y eventos de fallo | ❌ No implementado |
| A9 | **Respuestas correctas ante entradas inválidas** — validación robusta en la CLI | ❌ Sin manejo de errores en los scripts de cliente |
| A10 | **Herramienta de gestión de tareas** — evidencia de asignación y seguimiento del equipo | ❌ No evidenciado en el repositorio (penalidad del 30%) |
| A11 | **Plantilla de autoevaluación** | ❌ No evidenciada en el repositorio (penalidad del 10%) |
| A12 | **Pre-informe individual** | ❌ No evidenciado en el repositorio (invalida la evaluación grupal si no fue entregado) |
| A13 | **Tamaño de archivo y metadatos extendidos** en el NameNode (tamaño de bloques, checksum) | ❌ El modelo `BlockMetadata` solo guarda `block_id` y `replicas` |

### 1.4 Desviaciones relevantes

| Desviación | Descripción | Impacto |
|------------|-------------|---------|
| **Tamaño de bloque** | El enunciado establece 64 MB como valor por defecto; el proyecto usa 1 MB sin justificación documentada | Incumplimiento de requisito funcional explícito |
| **Nombre del directorio DataNode** | El directorio se llama `nodo de datos` (con espacio) en lugar de `datanode`, y en `docker-compose.yml` el `build` apunta a `./datanode` — esto causa **error en el build** | El sistema no puede desplegarse con `docker-compose up --build` |
| **Extensión del Dockerfile del DataNode** | El archivo se llama `Dockerfile.txt` y Docker no lo reconoce automáticamente | Falla silenciosa durante el build |
| **Archivos temporales con ruta Linux** | `dfs_client.py` usa `/tmp/{block_id}` — ruta exclusiva de Linux/macOS | Falla en entornos Windows o si la imagen Docker no es Linux |
| **IPs hardcodeadas** | Las URLs de NameNode y DataNodes están fijadas al IP de la instancia EC2 | Impide ejecución local y dificulta portabilidad |

---

## 2. Análisis Frente a los Criterios de Evaluación

### Criterio 1 — Diseño Arquitectónico y Documentación (20%)

| Aspecto evaluado | Estado | Observación |
|------------------|--------|-------------|
| Claridad en la definición de componentes | ✅ Cumplido | `README.md` y `CONTEXT.md` documentan los 4 componentes |
| Diagramas de arquitectura y flujos de datos | ⚠️ Parcial | Existe diagrama ASCII en el README, pero no hay diagramas formales (UML, C4, secuencia) |
| Descripción de protocolos y APIs | ✅ Cumplido | `CONTEXT.md §5` documenta todos los endpoints |
| Documentación completa y entendible | ⚠️ Parcial | Falta documentar el flujo DataNode → NameNode, y no hay descripción de la estrategia ante fallos |

**Estimación de cumplimiento: 70–75% del criterio**  
**Área crítica:** ausencia de diagramas formales de secuencia y de arquitectura de despliegue.

---

### Criterio 2 — Gestión de Bloques y Metadatos (20%)

| Aspecto evaluado | Estado | Observación |
|------------------|--------|-------------|
| Particionamiento de archivos en bloques | ✅ Cumplido | Implementado en `dfs_client.py` con bloques de 1 MB |
| Replicación correcta | ⚠️ Parcial | Se replica en escritura, pero no hay garantía dinámica si un nodo cae |
| Registro de metadatos en el NameNode | ✅ Cumplido | `POST /files/register` guarda en MongoDB |
| Recuperación de metadatos | ✅ Cumplido | `GET /files/{filename}` retorna bloques y réplicas |
| Reconstrucción de archivos a partir de bloques | ✅ Cumplido | `dfs_get.py` concatena bloques en orden |
| Manejo de errores por bloques faltantes o corruptos | ❌ Ausente | No hay validación de integridad (checksums) ni recuperación ante corrupción |
| Replicación activa ante fallos | ❌ Ausente | No existe mecanismo de detección ni re-replicación |

**Estimación de cumplimiento: 55–65% del criterio**  
**Área crítica:** ausencia de checksums y de re-replicación activa.

---

### Criterio 3 — Implementación Funcional de CLI/API (20%)

| Aspecto evaluado | Estado | Observación |
|------------------|--------|-------------|
| CLI `put` | ✅ Cumplido | `dfs_client.py` |
| CLI `get` | ✅ Cumplido | `dfs_get.py` |
| CLI `ls` | ❌ Ausente | No implementado |
| CLI `rm` | ❌ Ausente | No implementado |
| CLI `mkdir` / `rmdir` | ❌ Ausente | No implementado |
| Autenticación básica de usuarios | ⚠️ Parcial | Login/register OK, pero el token no se usa en operaciones de archivo |
| Respuestas correctas ante errores y entradas inválidas | ❌ Ausente | Los scripts de cliente no validan argumentos ni manejan errores de red |
| API documentada para interacciones programáticas | ✅ Cumplido | FastAPI genera Swagger automático en `/docs` |

**Estimación de cumplimiento: 40–50% del criterio**  
**Área crítica:** 4 de 6 operaciones CLI están ausentes; la autenticación no protege las operaciones de archivo.

---

### Criterio 4 — Comunicación entre Nodos (15%)

| Aspecto evaluado | Estado | Observación |
|------------------|--------|-------------|
| Cliente ↔ NameNode: solicitud y entrega de metadatos | ✅ Cumplido | `allocate`, `register`, `get` funcionan |
| Cliente ↔ DataNodes: transferencia de bloques confiable | ⚠️ Parcial | Se transfieren bloques, pero sin verificación de integridad (sin checksum) |
| DataNodes ↔ NameNode: registro inicial y reporte de bloques | ❌ Ausente | Los DataNodes no se registran ni reportan bloques al NameNode |
| Manejo de fallas con replicación: detección, logs, re-replicación | ❌ Ausente | No existe heartbeat, ni detección de caídas, ni logs |

**Estimación de cumplimiento: 45–55% del criterio**  
**Área crítica:** la comunicación DataNode → NameNode y el manejo de fallas son completamente inexistentes.

---

### Criterio 5 — Resultados y Demostración en Entorno Distribuido (15%)

| Aspecto evaluado | Estado | Observación |
|------------------|--------|-------------|
| Ejecución en al menos 3 nodos distribuidos | ✅ Cumplido | 3 DataNodes en AWS EC2 |
| Subida y descarga de archivos sin errores | ✅ Cumplido | Flujo funcional documentado |
| Evidencia de distribución de bloques en los DataNodes | ⚠️ Parcial | El comportamiento existe pero no hay evidencia documentada (screenshots, logs) |
| Si un DataNode falla: sistema continúa operativo y garantiza replicación | ❌ Ausente | Sin mecanismo de detección ni recuperación |

**Estimación de cumplimiento: 55–65% del criterio**  
**Área crítica:** falta evidencia documentada y el comportamiento ante fallos no está implementado.

---

### Criterio 6 — Video e Informe Final (10%)

| Aspecto evaluado | Estado | Observación |
|------------------|--------|-------------|
| Video con todos los integrantes explicando diseño, desarrollo y ejecución | ❓ No evidenciado en el repositorio | Sin video: penalidad del 20% sobre la nota total del proyecto |
| Informe técnico completo | ⚠️ Parcial | `README.md` y `CONTEXT.md` cubren parte; falta sección de pruebas y resultados |
| Repositorio bien documentado | ⚠️ Parcial | Código sin comentarios internos; estructura incompleta (`Dockerfile.txt`) |

**Estimación de cumplimiento: 50–60% del criterio** (si el video no existe o no cumple el formato)

---

### Resumen de evaluación estimada

| Criterio | Peso | Cumplimiento estimado | Puntos estimados |
|----------|------|-----------------------|------------------|
| 1. Diseño y documentación | 20% | 72% | ~14.4 / 20 |
| 2. Gestión de bloques y metadatos | 20% | 60% | ~12.0 / 20 |
| 3. CLI/API funcional | 20% | 45% | ~9.0 / 20 |
| 4. Comunicación entre nodos | 15% | 50% | ~7.5 / 15 |
| 5. Demostración distribuida | 15% | 60% | ~9.0 / 15 |
| 6. Video e informe | 10% | 55% | ~5.5 / 10 |
| **Total sin penalidades** | **100%** | | **~57.4 / 100** |

> ⚠️ **Penalidades aplicables** (según el enunciado):  
> — Sin herramienta de gestión de tareas: máximo 70% → pérdida directa de hasta 30 puntos si el alcance supera ese umbral.  
> — Sin plantilla de autoevaluación: máximo 90%.  
> — Sin pre-informe individual: invalida la evaluación grupal.

---

## 3. Propuesta de Mejoras y Funcionalidades Faltantes

Las mejoras están ordenadas por criterio de evaluación impactado. Cada una incluye **qué** implementar, **cómo** hacerlo y el **resultado esperado**.

---

### MEJORA M1 — Completar la CLI: `ls`, `rm`, `mkdir`, `rmdir`

**Impacto:** Criterio 3 (CLI/API) +20% → de ~45% a ~85% en ese criterio.

**Qué se debe añadir:**

| Operación | Endpoint NameNode | Descripción |
|-----------|-------------------|-------------|
| `ls` | `GET /files` | Lista todos los archivos registrados del usuario autenticado |
| `rm` | `DELETE /files/{filename}` | Elimina metadata del NameNode y ordena borrar bloques de DataNodes |
| `mkdir` | `POST /directories` | Crea un registro de directorio en MongoDB |
| `rmdir` | `DELETE /directories/{path}` | Elimina directorio y sus archivos asociados |

**Cómo implementarlo:**

1. En `namenode/app/main.py`, agregar los endpoints:
   ```python
   @app.get("/files")
   def list_files(token: str = Header(...)):
       username = verify_token(token)
       files = files_collection.find({"owner": username})
       return {"files": [f["filename"] for f in files]}

   @app.delete("/files/{filename}")
   def delete_file(filename: str, token: str = Header(...)):
       verify_token(token)
       file = files_collection.find_one({"filename": filename})
       # Notificar a cada DataNode para borrar los bloques
       for block in file["blocks"]:
           for replica in block["replicas"]:
               requests.delete(f"{replica}/block/{block['block_id']}")
       files_collection.delete_one({"filename": filename})
       return {"message": "File deleted"}
   ```

2. En `namenode/app/database.py`, agregar colección `directories`.

3. En `client/`, crear un script `dfs_cli.py` unificado con `argparse`:
   ```python
   parser.add_argument("command", choices=["put", "get", "ls", "rm", "mkdir", "rmdir"])
   ```

4. En `nodo de datos/app/main.py`, agregar:
   ```python
   @app.delete("/block/{block_id}")
   def delete_block(block_id: str):
       storage.delete_block(block_id)
       return {"message": "Block deleted"}
   ```

**Resultado esperado:** CLI completa que cumpla los 6 comandos del enunciado; el criterio 3 sube de ~45% a ~85%.

---

### MEJORA M2 — Proteger endpoints de archivos con autenticación JWT

**Impacto:** Criterios 3 y 4 — cierra la brecha de seguridad documentada en `CONTEXT.md §7`.

**Qué se debe corregir:**  
Los endpoints `/files/allocate`, `/files/register`, `/files/{filename}`, `DELETE /files/{filename}` y `GET /files` deben validar el token JWT.

**Cómo implementarlo:**

1. Crear función de verificación en `auth.py`:
   ```python
   def verify_token(token: str) -> str:
       try:
           payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
           return payload["username"]
       except jwt.InvalidTokenError:
           raise HTTPException(status_code=401, detail="Invalid token")
   ```

2. Agregar el campo `owner` al modelo `FileMetadata` y al documento MongoDB para que cada usuario solo acceda a sus propios archivos.

3. Inyectar el token en los scripts de cliente mediante variable de entorno `DFS_TOKEN` o archivo `.dfs_token` generado tras el login.

**Resultado esperado:** El sistema cumple el requisito de que cada cliente gestiona solo sus propios archivos mediante autenticación.

---

### MEJORA M3 — Tamaño de bloque configurable (valor por defecto: 64 MB)

**Impacto:** Criterio 2 (gestión de bloques) y Criterio 3 (CLI).

**Qué se debe modificar:**

- `client/dfs_client.py`: reemplazar `BLOCK_SIZE = 1024 * 1024` por:
  ```python
  import os
  BLOCK_SIZE = int(os.getenv("DFS_BLOCK_SIZE", 64 * 1024 * 1024))  # 64 MB por defecto
  ```

- `docker-compose.yml` y los `Dockerfile` de cliente: exponer la variable de entorno `DFS_BLOCK_SIZE`.

- Documentar en el `README.md` cómo configurar el tamaño de bloque.

**Resultado esperado:** Cumplimiento del requisito explícito del enunciado ("valor por defecto de 64 MB", "configurable"). Elimina la desviación documentada en `CONTEXT.md §10`.

---

### MEJORA M4 — Heartbeat y registro DataNode → NameNode

**Impacto:** Criterio 4 (comunicación entre nodos) — el aspecto más deficiente con 0% de cumplimiento.

**Qué se debe añadir:**

1. **Endpoint de registro** en el NameNode:
   ```python
   @app.post("/datanodes/register")
   def register_datanode(node_url: str, node_id: str):
       datanodes_collection.update_one(
           {"node_id": node_id},
           {"$set": {"url": node_url, "last_seen": datetime.utcnow(), "status": "alive"}},
           upsert=True
       )
       return {"message": "DataNode registered"}
   ```

2. **Endpoint de heartbeat** en el NameNode:
   ```python
   @app.post("/datanodes/heartbeat")
   def heartbeat(node_id: str):
       datanodes_collection.update_one(
           {"node_id": node_id},
           {"$set": {"last_seen": datetime.utcnow(), "status": "alive"}}
       )
       return {"status": "ok"}
   ```

3. **Tarea de fondo en el DataNode** que envíe el heartbeat cada 30 segundos al NameNode usando `asyncio` o `threading`:
   ```python
   import threading, time, requests, os

   def heartbeat_loop():
       while True:
           try:
               requests.post(f"{NAMENODE_URL}/datanodes/heartbeat",
                             params={"node_id": NODE_ID})
           except Exception:
               pass
           time.sleep(30)

   threading.Thread(target=heartbeat_loop, daemon=True).start()
   ```

4. **Job de monitoreo en el NameNode** que marque como `dead` los DataNodes que no hayan enviado heartbeat en los últimos 90 segundos.

**Resultado esperado:** El NameNode sabe en todo momento qué DataNodes están vivos, base necesaria para la re-replicación activa (M5).

---

### MEJORA M5 — Detección de fallos y re-replicación activa

**Impacto:** Criterios 2, 4 y 5 — requisito explícito del enunciado: "Si un DataNode falla: el sistema continúa operativo e inicia la garantía de replicación".

**Qué se debe añadir:**

1. Al detectar un DataNode como `dead` (ver M4), el NameNode ejecuta una **tarea de re-replicación**:
   - Consulta todos los archivos cuyos bloques tienen réplicas en ese DataNode.
   - Para cada bloque afectado, selecciona un DataNode vivo que ya tenga el bloque y ordena al NameNode que lo copie a otro DataNode vivo disponible.

2. Estrategia simplificada (sin comunicación directa entre DataNodes):
   ```
   1. NameNode detecta DataNode X como dead.
   2. Busca bloques con réplica en X que ahora tienen solo 1 copia.
   3. Descarga el bloque desde la réplica sobreviviente.
   4. Lo sube a un DataNode sano diferente.
   5. Actualiza la metadata en MongoDB.
   ```

3. Agregar logs de este proceso (ver M7).

**Resultado esperado:** El criterio 5 sube a ~85–90%, dado que el enunciado valora explícitamente este comportamiento.

---

### MEJORA M6 — Validación de integridad de bloques (checksum)

**Impacto:** Criterio 2 (manejo de bloques faltantes o corruptos).

**Qué se debe añadir:**

1. En `dfs_client.py`, calcular el hash SHA-256 de cada bloque antes de subirlo:
   ```python
   import hashlib
   checksum = hashlib.sha256(chunk).hexdigest()
   ```

2. Incluir el checksum en la metadata enviada al NameNode (`POST /files/register`).

3. Actualizar el modelo `BlockMetadata`:
   ```python
   class BlockMetadata(BaseModel):
       block_id: str
       replicas: List[str]
       checksum: str       # SHA-256 del bloque
       size_bytes: int     # Tamaño real del bloque
   ```

4. En `dfs_get.py`, verificar el checksum de cada bloque descargado; si no coincide, intentar la siguiente réplica.

**Resultado esperado:** Cumplimiento del requisito de "manejo básico de errores por bloques faltantes o corruptos".

---

### MEJORA M7 — Sistema de logs estructurados

**Impacto:** Criterios 4 y 5 — el enunciado requiere explícitamente "logs del sistema".

**Qué se debe añadir:**

En todos los componentes (NameNode y DataNode), configurar el logger estándar de Python:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("dfs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

Eventos a registrar obligatoriamente:
- Registro/login de usuario
- Asignación de bloques (`allocate`)
- Subida y descarga de bloques
- Heartbeat recibido / DataNode marcado como dead
- Inicio de proceso de re-replicación
- Errores de red con traza completa

**Resultado esperado:** Trazabilidad completa del sistema; evidencia verificable para la demostración.

---

### MEJORA M8 — Corregir errores de despliegue (bloqueantes)

**Impacto:** Criterio 5 — sin esto el sistema no puede desplegarse desde el repositorio.

**Qué se debe corregir:**

| Problema | Corrección |
|----------|------------|
| `nodo de datos/Dockerfile.txt` | Renombrar a `nodo de datos/Dockerfile` |
| `docker-compose.yml` apunta a `./datanode` | Cambiar a `./nodo de datos` o renombrar el directorio a `datanode` |
| IPs hardcodeadas en `main.py` y scripts de cliente | Reemplazar por variables de entorno con valores por defecto para desarrollo local |

```yaml
# docker-compose.yml corregido (fragmento)
  datanode1:
    build: ./datanode          # directorio renombrado
    environment:
      - NODE_ID=datanode1
      - NAMENODE_URL=http://namenode:8000
      - PORT=8001
```

```python
# namenode/app/main.py corregido
import os
DATANODES = os.getenv("DATANODES", "http://datanode1:8001,http://datanode2:8001,http://datanode3:8001").split(",")
```

**Resultado esperado:** `docker-compose up --build` funciona sin intervención manual; el sistema es reproducible por cualquier evaluador.

---

### MEJORA M9 — Documentación complementaria (diagramas formales y pruebas)

**Impacto:** Criterios 1 y 6.

**Qué se debe añadir en `docs/`:**

1. **Diagrama de secuencia** (PUT y GET) en formato Mermaid o imagen exportada, mostrando el flujo completo incluyendo heartbeat y re-replicación.
2. **Diagrama de arquitectura de despliegue** mostrando las instancias EC2, puertos expuestos y red Docker.
3. **Sección de pruebas y resultados** en el informe: capturas de pantalla de la subida de archivos, distribución de bloques en cada DataNode, y simulación de caída de un nodo.
4. **Autoevaluación** en el formato requerido por el docente (penalidad del 10% si no se entrega).

---

### MEJORA M10 — Evidenciar herramienta de gestión de tareas

**Impacto:** Penalidad del 30% sobre la nota total si no se presenta.

**Qué se debe añadir:**

- Crear un tablero en GitHub Projects, Trello o Jira con las tareas de este proyecto, asignadas por integrante, con fechas y estado.
- Incluir en el repositorio un `docs/TASK_MANAGEMENT.md` con el enlace al tablero y una captura de pantalla del estado actual.
- El enunciado requiere evidencia de: **asignación**, **seguimiento**, **priorización** y **cumplimiento** por integrante.

**Resultado esperado:** Eliminación de la penalidad del 30%, la de mayor impacto en la nota.

---

## 4. Plan de Acción Priorizado

El orden está determinado por la combinación de **impacto en la nota** (penalidades primero, luego criterios de mayor peso) y **dependencias técnicas** entre mejoras.

---

### 🔴 PRIORIDAD CRÍTICA — Penalidades y bloqueantes (impacto inmediato en nota)

| Paso | Acción | Mejora | Tiempo estimado | Impacto |
|------|--------|--------|-----------------|---------|
| **1** | Crear tablero de gestión de tareas (GitHub Projects o Trello) y documentarlo en `docs/TASK_MANAGEMENT.md` | M10 | 1–2 horas | Evita penalidad del **30%** |
| **2** | Corregir `Dockerfile.txt` → `Dockerfile` y alinear `docker-compose.yml` con el nombre real del directorio del DataNode | M8 | 30 min | Sistema desplegable; elimina error bloqueante en Criterio 5 |
| **3** | Reemplazar IPs hardcodeadas por variables de entorno en NameNode y scripts de cliente | M8 | 1 hora | Portabilidad; requisito para evaluación reproducible |
| **4** | Entregar plantilla de autoevaluación al docente | M9 | 1 hora | Evita penalidad del **10%** |

---

### 🟠 PRIORIDAD ALTA — Criterios 3 y 2 (40% de la nota total)

| Paso | Acción | Mejora | Tiempo estimado | Impacto en criterio |
|------|--------|--------|-----------------|---------------------|
| **5** | Implementar `verify_token()` y aplicarlo a todos los endpoints de archivos | M2 | 2 horas | Criterio 3: autenticación completa |
| **6** | Implementar script CLI unificado `dfs_cli.py` con `ls` y `rm` | M1 | 3–4 horas | Criterio 3: de ~45% a ~70% |
| **7** | Implementar `mkdir` y `rmdir` en NameNode y CLI | M1 | 2 horas | Criterio 3: de ~70% a ~85% |
| **8** | Hacer configurable el tamaño de bloque (variable de entorno `DFS_BLOCK_SIZE`, valor por defecto 64 MB) | M3 | 1 hora | Criterio 2: elimina desviación explícita del enunciado |
| **9** | Agregar checksum SHA-256 al modelo `BlockMetadata` y verificación en descarga | M6 | 2–3 horas | Criterio 2: manejo de corrupción |

---

### 🟡 PRIORIDAD MEDIA — Criterios 4 y 5 (30% de la nota total)

| Paso | Acción | Mejora | Tiempo estimado | Impacto en criterio |
|------|--------|--------|-----------------|---------------------|
| **10** | Implementar endpoint `POST /datanodes/register` y `POST /datanodes/heartbeat` en el NameNode | M4 | 2–3 horas | Criterio 4: registro DataNode → NameNode |
| **11** | Implementar hilo de heartbeat en cada DataNode (cada 30 s) | M4 | 1–2 horas | Criterio 4: comunicación continua |
| **12** | Implementar job de monitoreo en NameNode que detecte DataNodes caídos | M5 | 2 horas | Criterio 4 y 5: detección de fallos |
| **13** | Implementar re-replicación activa al detectar un DataNode muerto | M5 | 3–4 horas | Criterio 5: de ~60% a ~85% |
| **14** | Configurar logs estructurados en todos los componentes | M7 | 2 horas | Criterios 4 y 5: trazabilidad y evidencia |

---

### 🟢 PRIORIDAD NORMAL — Documentación y entregables (Criterio 1 y 6)

| Paso | Acción | Mejora | Tiempo estimado | Impacto en criterio |
|------|--------|--------|-----------------|---------------------|
| **15** | Añadir diagramas formales de secuencia (PUT, GET, heartbeat, re-replicación) en `docs/` | M9 | 2–3 horas | Criterio 1: de ~72% a ~90% |
| **16** | Agregar diagrama de despliegue AWS (instancias, puertos, red) | M9 | 1–2 horas | Criterio 1: documentación completa |
| **17** | Documentar sección de pruebas y resultados (capturas, logs, simulación de fallo) | M9 | 2–3 horas | Criterio 6: informe técnico completo |
| **18** | Grabar video de demostración (≤30 min) con participación de todos los integrantes | M9 | 3–5 horas | Criterio 6: sin video → penalidad del 20% |

---

### Estimación de nota proyectada tras implementar el plan

| Criterio | Peso | Antes | Después (estimado) |
|----------|------|-------|--------------------|
| 1. Diseño y documentación | 20% | ~72% | ~90% → **18.0 / 20** |
| 2. Gestión de bloques | 20% | ~60% | ~85% → **17.0 / 20** |
| 3. CLI/API funcional | 20% | ~45% | ~85% → **17.0 / 20** |
| 4. Comunicación entre nodos | 15% | ~50% | ~80% → **12.0 / 15** |
| 5. Demostración distribuida | 15% | ~60% | ~85% → **12.8 / 15** |
| 6. Video e informe | 10% | ~55% | ~85% → **8.5 / 10** |
| **Total sin penalidades** | | **~57.4** | **~85.3 / 100** |
| **Menos: sin gestión de tareas** | | **−30** | **0** (M10 lo evita) |
| **Menos: sin autoevaluación** | | **−10** | **0** (paso 4 lo evita) |
| **Nota final estimada** | | ~40–50 | **~83–87 / 100** |

> La ganancia más significativa proviene de los **pasos 1, 4, 5, 6 y 7**, que en conjunto evitan las penalidades y cubren el 40% de la nota en los criterios de mayor peso.

---

*Documento generado a partir del análisis de `CONTEXT.md` y `Proyecto-dfs-v2.docx`. Todas las estimaciones de cumplimiento son conservadoras y están basadas exclusivamente en el código y la documentación presentes en el repositorio.*
