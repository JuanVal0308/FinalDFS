# Diagrama de despliegue — AWS EC2

```mermaid
flowchart TB
    subgraph Internet
        CLI[Cliente dfs_cli.py]
    end

    subgraph EC2["EC2 52.23.74.126"]
        subgraph Docker["Docker Compose — red dfsnet"]
            NN[namenode :8000]
            D1[datanode1 :8001]
            D2[datanode2 :8002]
            D3[datanode3 :8003]
        end
    end

    subgraph Atlas["MongoDB Atlas"]
        MDB[(dfs_system)]
    end

    CLI -->|:8000 JWT, metadata| NN
    CLI -->|:8001-8003 bloques| D1
    CLI -->|:8001-8003 bloques| D2
    CLI -->|:8001-8003 bloques| D3
    NN --> MDB
    D1 -->|heartbeat interno| NN
    D2 -->|heartbeat interno| NN
    D3 -->|heartbeat interno| NN
    NN -->|re-replicación interna| D2
    NN -->|re-replicación interna| D3
```

## Puertos expuestos (Security Group)

| Puerto | Servicio |
|--------|----------|
| 22 | SSH |
| 8000 | NameNode |
| 8001 | DataNode 1 |
| 8002 | DataNode 2 |
| 8003 | DataNode 3 |

## Variables clave

| Archivo | Variable | Valor en producción |
|---------|----------|---------------------|
| `.env` | `PUBLIC_IP` | `52.23.74.126` |
| `namenode/.env` | `MONGO_URI` | MongoDB Atlas |
| `namenode/.env` | `JWT_SECRET` | Clave del servidor |
