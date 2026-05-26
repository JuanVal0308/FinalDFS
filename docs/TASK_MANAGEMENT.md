# 📋 Gestión de Tareas — FinalDFS

> Este documento evidencia el uso de una herramienta de gestión de tareas tal como lo exige el enunciado del proyecto (penalidad del 30% ante su ausencia).

---

## Herramienta utilizada: GitHub Projects

**Tablero:** [FinalDFS — Sprint Board](https://github.com/users/JoseVelez/projects/1)
*(Actualizar con el enlace real del tablero una vez creado)*

---

## Estructura del tablero

| Columna | Descripción |
|---------|-------------|
| **Backlog** | Tareas identificadas, aún no iniciadas |
| **En progreso** | Tarea actualmente en desarrollo |
| **En revisión** | Completada, pendiente de validación |
| **Hecho** | Verificada y cerrada |

---

## Sprint 1 — Implementación base ✅

| ID | Tarea | Responsable | Estado |
|----|-------|-------------|--------|
| T-01 | NameNode: endpoints allocate, register, get | Jose_Velezg | ✅ Hecho |
| T-02 | DataNode: upload y get de bloques | JuanVal0308 | ✅ Hecho |
| T-03 | Cliente: script de subida `put` | JuanVal0308 | ✅ Hecho |
| T-04 | Cliente: script de descarga `get` | JuanVal0308 | ✅ Hecho |
| T-05 | Autenticación JWT + bcrypt | Jose_Velezg | ✅ Hecho |
| T-06 | Conexión MongoDB Atlas | Jose_Velezg | ✅ Hecho |
| T-07 | Dockerizar todos los servicios | Jose_Velezg | ✅ Hecho |
| T-08 | Desplegar en AWS EC2 | Ambos | ✅ Hecho |
| T-09 | README.md inicial | Jose_Velezg | ✅ Hecho |

---

## Sprint 2 — Mejoras y completitud ✅

| ID | Tarea | Responsable | Estado |
|----|-------|-------------|--------|
| T-10 | Corregir rutas Docker (`nodo de datos` → `datanode`) | Jose_Velezg | ✅ Hecho |
| T-11 | Aplicar JWT a todos los endpoints de archivos | Jose_Velezg | ✅ Hecho |
| T-12 | CLI: `ls` | Jose_Velezg | ✅ Hecho |
| T-13 | CLI: `rm` | Jose_Velezg | ✅ Hecho |
| T-14 | CLI: `mkdir` / `rmdir` | Jose_Velezg | ✅ Hecho |
| T-15 | CLI unificada con argparse (`dfs_cli.py`) | Jose_Velezg | ✅ Hecho |
| T-16 | Tamaño de bloque configurable (`DFS_BLOCK_SIZE`, default 64 MB) | Jose_Velezg | ✅ Hecho |
| T-17 | Checksum SHA-256 por bloque | Jose_Velezg | ✅ Hecho |
| T-18 | Logs estructurados en NameNode y DataNode | Jose_Velezg | ✅ Hecho |
| T-19 | IPs hardcodeadas → variables de entorno (`PUBLIC_IP`) | Jose_Velezg | ✅ Hecho |

---

## Sprint 3 — Tolerancia a fallos · JuanVal0308 ✅

> **Rama:** `feature/heartbeat-replication` (fusionado en `main`)  
> **Despliegue:** EC2 `52.23.74.126` — NameNode `:8000`, DataNodes `:8001`–`:8003`

### Código

| ID | Tarea | Archivo | Estado |
|----|-------|---------|--------|
| T-20 | Agregar colección `datanodes` en MongoDB | `namenode/app/database.py` | ✅ Hecho |
| T-21 | Endpoint `POST /datanodes/register` | `namenode/app/main.py` | ✅ Hecho |
| T-22 | Endpoint `POST /datanodes/heartbeat` | `namenode/app/main.py` | ✅ Hecho |
| T-23 | Endpoint `GET /datanodes` | `namenode/app/main.py` | ✅ Hecho |
| T-24 | Hilo de heartbeat en el DataNode al arrancar | `datanode/app/main.py` | ✅ Hecho |
| T-25 | Job de monitoreo: detectar nodos sin heartbeat en >90 s | `namenode/app/main.py` | ✅ Hecho |
| T-26 | Re-replicación activa al detectar nodo caído | `namenode/app/main.py` | ✅ Hecho |

### Documentación

| ID | Tarea | Archivo | Estado |
|----|-------|---------|--------|
| T-27 | Redactar §6 del informe: algoritmos de distribución, replicación y re-replicación | `docs/INFORME.md` | ✅ Hecho |
| T-28 | Redactar §8 del informe: pruebas de tolerancia a fallos con capturas | `docs/INFORME.md` | ✅ Hecho |

---

## Sprint 3 — Documentación e Informe · Sara ✅

> **Rama:** `feature/docs-informe` (fusionado en `main`)

### Código

| ID | Tarea | Archivo | Estado |
|----|-------|---------|--------|
| T-29 | Comando `status` en la CLI: muestra estado de cada DataNode | `client/dfs_cli.py` | ✅ Hecho |

### Documentación

| ID | Tarea | Archivo | Estado |
|----|-------|---------|--------|
| T-30 | Diagrama de secuencia: flujo PUT | `docs/diagrams/seq_put.md` | ✅ Hecho |
| T-31 | Diagrama de secuencia: flujo GET con failover | `docs/diagrams/seq_get.md` | ✅ Hecho |
| T-32 | Diagrama de secuencia: heartbeat y re-replicación | `docs/diagrams/seq_heartbeat.md` | ✅ Hecho |
| T-33 | Diagrama de despliegue AWS (EC2, contenedores, puertos) | `docs/diagrams/deploy_aws.md` | ✅ Hecho |
| T-34 | Redactar §1–§5 y §7 del informe | `docs/INFORME.md` | ✅ Hecho |
| T-35 | Redactar §9 del informe: conclusiones | `docs/INFORME.md` | ✅ Hecho |
| T-36 | Plantilla de autoevaluación (exportar PDF para el docente) | `docs/AUTOEVALUACION.md` | ✅ Hecho |

**Estructura de `docs/INFORME.md`:**

| Sección | Responsable |
|---------|-------------|
| §1 Objetivo | Integrante 4 |
| §2 Marco Teórico | Integrante 4 |
| §3 Descripción del servicio | Integrante 4 |
| §4 Arquitectura del sistema | Integrante 4 |
| §5 Protocolos y APIs | Integrante 4 |
| §6 Algoritmos | Integrante 3 |
| §7 Entorno de ejecución | Integrante 4 |
| §8 Pruebas y resultados | Integrante 3 |
| §9 Conclusiones | Integrante 4 |

---

## Dependencia entre Integrante 3 e Integrante 4

```
JuanVal0308 termina T-23 (GET /datanodes)
        ↓
Sara implementa T-29 (comando status)
        ↓
JuanVal0308 incluye status en las capturas de la demo (T-28)
```

Todo lo demás puede hacerse en paralelo desde el primer día.

---

## Resumen de colaboración en el repositorio

| Integrante | Archivos de código | Archivos de docs |
|------------|-------------------|-----------------|
| Jose_Velezg | `namenode/app/*`, `datanode/app/*`, `client/dfs_cli.py`, `docker-compose.yml` | `README.md`, `docs/CONTEXT.md`, `docs/TASK_MANAGEMENT.md` |
| JuanVal0308 | `namenode/app/main.py`, `namenode/app/database.py`, `datanode/app/main.py` | `docs/INFORME.md` (§6, §8) |
| Sara | `client/dfs_cli.py` (comando `status`) | `docs/INFORME.md` (§1–§5, §7, §9), `docs/diagrams/*` |

---

## Convenciones de commits

```
feat(namenode): agregar endpoint POST /datanodes/heartbeat
feat(datanode): iniciar hilo de heartbeat al arrancar
feat(client): agregar comando status al CLI
docs(informe): redactar seccion de algoritmos
docs(diagrams): agregar diagrama de secuencia flujo PUT
```
