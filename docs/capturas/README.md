# Capturas de pruebas — Informe §8

Coloca aquí las imágenes de la demostración. Guion completo: [GUIA_DEMO.md](../GUIA_DEMO.md).

| Archivo | Qué capturar |
|---------|----------------|
| `01_estado_inicial.png` | `docker compose ps` + `python3 dfs_cli.py status` (3 alive) |
| `02_put_ls.png` | Salida de `put` y `ls` |
| `03_bloques_datanodes.png` | `curl localhost:800{1,2,3}/blocks` con block_id visible |
| `04_metadata.png` | `GET /files/{archivo}` con réplicas y checksum |
| `05_nodo_detenido.png` | `docker stop datanode1` + `docker compose ps` |
| `06_get_failover.png` | `get` exitoso con datanode1 caído |
| `07_nodo_dead.png` | `/datanodes` con `status: dead` tras ~2 min |
| `08_rereplicacion.png` | Logs NameNode o metadata sin réplica caída |
| `09_recuperacion.png` | 3 nodos `alive` tras reinicio |
| `10_archivo_grande.png` | (Opcional) `put` de Alvarito.bin — 4 bloques |

## Comandos rápidos

```bash
# Metadata con token
cd ~/FinalDFS/client
TOKEN=$(cat .dfs_token)
curl -s "http://localhost:8000/files/archivo1.txt" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
