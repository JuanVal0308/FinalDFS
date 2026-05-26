# Capturas de pruebas (§8 del informe)

Coloca aquí las capturas de la demostración de tolerancia a fallos:

| Archivo sugerido | Contenido |
|------------------|-----------|
| `01_estado_inicial_datanodes.png` | `docker compose ps` + `GET /datanodes` (3 alive) |
| `02_put_y_ls.png` | `dfs_cli.py put` y `ls` |
| `03_bloques_en_datanodes.png` | `curl .../blocks` en 2 nodos |
| `04_metadata_replicas.png` | JSON de `/files/{filename}` |
| `05_datanode1_detenido.png` | `docker stop datanode1` |
| `06_get_con_nodo_caido.png` | `dfs_cli.py get` exitoso |
| `07_nodo_dead.png` | `/datanodes` con status dead |
| `08_rereplicacion.png` | Logs o metadata actualizada |
| `09_recuperacion.png` | 3 nodos alive de nuevo |
| `10_status_cli.png` | `python dfs_cli.py status` |

Comandos detallados: ver guía en el chat del proyecto o `docs/INFORME.md` §8.
