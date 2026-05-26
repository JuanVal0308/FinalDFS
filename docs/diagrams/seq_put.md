# Diagrama de secuencia — Flujo PUT

```mermaid
sequenceDiagram
    participant C as Cliente (dfs_cli)
    participant N as NameNode :8000
    participant D1 as DataNode 1 :8001
    participant D2 as DataNode 2 :8002

    C->>N: POST /auth/login
    N-->>C: JWT token

    C->>N: GET /files/allocate/{file}/{n} (Bearer)
    N-->>C: blocks + réplicas (Round-Robin)

    loop Por cada bloque
        C->>D1: POST /block/upload/{block_id}
        D1-->>C: 200 OK
        C->>D2: POST /block/upload/{block_id}
        D2-->>C: 200 OK
    end

    C->>N: POST /files/register (metadata + checksum)
    N-->>C: File registered
```

## Descripción

1. El cliente autentica y obtiene JWT.
2. El NameNode asigna bloques con factor de replicación 2.
3. El cliente sube cada bloque directamente a las réplicas.
4. Se registra la metadata en MongoDB.
