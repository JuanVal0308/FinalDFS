# 📋 Gestión de Tareas — FinalDFS

> Este documento evidencia el uso de una herramienta de gestión de tareas tal como lo exige el enunciado del proyecto (penalidad del 30% ante su ausencia).

---

## Herramienta utilizada: GitHub Projects

**Tablero:** [FinalDFS — Sprint Board](https://github.com/users/JoseVelez/projects/1)
*(Actualizar con el enlace real del tablero una vez creado)*

---

## Estructura del tablero

El tablero usa columnas Kanban con los estados:

| Columna | Descripción |
|---------|-------------|
| **Backlog** | Tareas identificadas, aún no iniciadas |
| **En progreso** | Tarea actualmente en desarrollo |
| **En revisión** | Tarea completada, pendiente de validación del compañero |
| **Hecho** | Tarea verificada y cerrada |

---

## Tareas del proyecto (Sprint 1 — Implementación base)

| ID | Tarea | Responsable | Prioridad | Estado |
|----|-------|-------------|-----------|--------|
| T-01 | Implementar NameNode: endpoints allocate, register, get | Jose_Velezg | Alta | ✅ Hecho |
| T-02 | Implementar DataNode: upload y get de bloques | JuanVal0308 | Alta | ✅ Hecho |
| T-03 | Implementar cliente: script de subida (`put`) | JuanVal0308 | Alta | ✅ Hecho |
| T-04 | Implementar cliente: script de descarga (`get`) | JuanVal0308 | Alta | ✅ Hecho |
| T-05 | Configurar autenticación JWT + bcrypt | Jose_Velezg | Alta | ✅ Hecho |
| T-06 | Conectar MongoDB Atlas al NameNode | Jose_Velezg | Alta | ✅ Hecho |
| T-07 | Dockerizar todos los servicios | Jose_Velezg | Alta | ✅ Hecho |
| T-08 | Desplegar en AWS EC2 | Ambos | Alta | ✅ Hecho |
| T-09 | Escribir README.md | Jose_Velezg | Media | ✅ Hecho |

---

## Tareas del proyecto (Sprint 2 — Mejoras y completitud)

| ID | Tarea | Responsable | Prioridad | Estado |
|----|-------|-------------|-----------|--------|
| T-10 | Corregir rutas Docker (`nodo de datos` → `datanode`) | Jose_Velezg | Crítica | ✅ Hecho |
| T-11 | Aplicar autenticación JWT a todos los endpoints | Jose_Velezg | Crítica | ✅ Hecho |
| T-12 | Implementar CLI: `ls` (listar archivos) | Jose_Velezg | Alta | ✅ Hecho |
| T-13 | Implementar CLI: `rm` (eliminar archivo) | Jose_Velezg | Alta | ✅ Hecho |
| T-14 | Implementar CLI: `mkdir` / `rmdir` | Jose_Velezg | Alta | ✅ Hecho |
| T-15 | CLI unificada con argparse (`dfs_cli.py`) | Jose_Velezg | Alta | ✅ Hecho |
| T-16 | Tamaño de bloque configurable (env `DFS_BLOCK_SIZE`) | Jose_Velezg | Alta | ✅ Hecho |
| T-17 | Checksum SHA-256 por bloque en subida/bajada | Jose_Velezg | Media | ✅ Hecho |
| T-18 | Logs estructurados en NameNode y DataNode | Jose_Velezg | Media | ✅ Hecho |
| T-19 | Reemplazar IPs hardcodeadas por variables de entorno | Jose_Velezg | Alta | ✅ Hecho |
| T-20 | Implementar heartbeat DataNode → NameNode | JuanVal0308 | Media | 🔄 En progreso |
| T-21 | Re-replicación activa ante fallo de DataNode | JuanVal0308 | Media | 📋 Backlog |
| T-22 | Redactar informe técnico final | Ambos | Alta | 📋 Backlog |
| T-23 | Grabar video de demostración | Ambos | Crítica | 📋 Backlog |
| T-24 | Completar plantilla de autoevaluación | Ambos | Crítica | 📋 Backlog |

---

## Convenciones de commits

Todos los commits siguen el formato:

```
<tipo>(<alcance>): <descripción breve>

Ejemplos:
feat(namenode): agregar endpoint GET /files para listar archivos
fix(docker): corregir build path del DataNode en docker-compose.yml
docs(readme): actualizar instrucciones de despliegue
```

---

## Evidencia de participación

| Integrante | Commits principales |
|------------|---------------------|
| Jose_Velezg | NameNode, MongoDB, Auth, Docker, CLI mejoras, CI/CD |
| JuanVal0308 | DataNode, scripts de cliente put/get, Dockerfile cliente |

> **Nota:** La distribución de tareas está reflejada en el historial de git del repositorio y en el tablero de GitHub Projects.
