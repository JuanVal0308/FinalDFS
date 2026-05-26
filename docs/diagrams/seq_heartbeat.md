# Diagrama de secuencia — Heartbeat y re-replicación

```mermaid
sequenceDiagram
    participant DN as DataNode
    participant N as NameNode
    participant DB as MongoDB
    participant DV as DataNode vivo

    Note over DN,N: Al arrancar
    DN->>N: POST /datanodes/register
    N->>DB: upsert datanodes (alive)
    N-->>DN: OK

    loop Cada 30 s
        DN->>N: POST /datanodes/heartbeat
        N->>DB: actualizar last_seen
    end

    Note over N: Monitor cada 30 s
    N->>DB: nodos sin heartbeat > 90 s
    N->>DB: status = dead
    N->>DV: GET bloque (réplica sobreviviente)
    N->>DV: POST /block/upload (nueva réplica)
    N->>DB: actualizar replicas en files
```

## Descripción

- Los DataNodes se registran y envían heartbeat periódico.
- El NameNode marca nodos inactivos como `dead`.
- Se re-replican bloques huérfanos hacia nodos vivos.
