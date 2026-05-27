# Documentación — FinalDFS

Índice de la documentación del proyecto.

| Documento | Descripción |
|-----------|-------------|
| [README.md](../README.md) | Guía principal: arquitectura, despliegue, CLI y API |
| [GUIA_EC2.md](GUIA_EC2.md) | Despliegue y operación en AWS EC2 |
| [GUIA_DEMO.md](GUIA_DEMO.md) | Guion de demostración (video / informe §8) |
| [CONTEXT.md](CONTEXT.md) | Contexto técnico detallado del sistema |
| [INFORME.md](INFORME.md) | Informe académico (§1–§9) |
| [TASK_MANAGEMENT.md](TASK_MANAGEMENT.md) | Gestión de tareas y sprints |
| [AUTOEVALUACION.md](AUTOEVALUACION.md) | Plantilla de autoevaluación |
| [PROPUESTA_DE_MEJORA.md](PROPUESTA_DE_MEJORA.md) | Análisis de brechas vs. enunciado |

## Diagramas (`docs/diagrams/`)

| Archivo | Contenido |
|---------|-----------|
| [seq_put.md](diagrams/seq_put.md) | Secuencia: subida de archivos |
| [seq_get.md](diagrams/seq_get.md) | Secuencia: descarga con failover |
| [seq_heartbeat.md](diagrams/seq_heartbeat.md) | Secuencia: heartbeat y re-replicación |
| [deploy_aws.md](diagrams/deploy_aws.md) | Despliegue en EC2 |

## Capturas de prueba

Ver [capturas/README.md](capturas/README.md) para la lista de evidencias del informe.

## URLs de producción (EC2)

| Servicio | URL |
|----------|-----|
| NameNode | http://52.23.74.126:8000 |
| Swagger | http://52.23.74.126:8000/docs |
| DataNode 1 | http://52.23.74.126:8001 |
| DataNode 2 | http://52.23.74.126:8002 |
| DataNode 3 | http://52.23.74.126:8003 |
