# Guía de despliegue en AWS EC2

Despliegue de FinalDFS en Ubuntu (EC2). IP de referencia: **52.23.74.126**.

---

## 1. Requisitos en la instancia

- Ubuntu 22.04 / 24.04 / 26.04
- Docker y Docker Compose
- Puertos abiertos en el Security Group: **22, 8000, 8001, 8002, 8003**
- Cluster MongoDB Atlas accesible desde la IP de la EC2 (Network Access en Atlas)

### Instalar Docker (Ubuntu)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

---

## 2. Clonar el repositorio

```bash
cd ~
git clone https://github.com/JuanVal0308/FinalDFS.git
cd FinalDFS
```

Si `git pull` falla por ramas divergentes:

```bash
git fetch origin
git reset --hard origin/main
```

---

## 3. Configurar variables de entorno

### Raíz del proyecto (`.env`)

```bash
cp .env.example .env
```

Contenido mínimo:

```env
PUBLIC_IP=52.23.74.126
```

### NameNode (`namenode/.env`)

```bash
cp namenode/.env.example namenode/.env
nano namenode/.env
```

Formato correcto (solo `CLAVE=valor`, sin código Python):

```env
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/?retryWrites=true&w=majority
JWT_SECRET=una_clave_secreta_larga
```

| Variable | Descripción |
|----------|-------------|
| `MONGO_URI` | Cadena de conexión MongoDB Atlas |
| `JWT_SECRET` | Clave del servidor para firmar JWT (no es la contraseña del usuario) |

---

## 4. Levantar servicios

```bash
cd ~/FinalDFS
docker compose up -d --build
```

Si los DataNodes arrancaron antes que el NameNode y no se registraron:

```bash
docker compose restart datanode1 datanode2 datanode3
sleep 10
curl -s http://localhost:8000/datanodes | python3 -m json.tool
```

Deben aparecer 3 nodos con `"status": "alive"`.

---

## 5. Verificación

```bash
docker compose ps
curl -s http://localhost:8000/ | python3 -m json.tool
curl -s http://localhost:8000/datanodes | python3 -m json.tool
```

Desde tu PC (con Security Group abierto):

```bash
curl http://52.23.74.126:8000/
curl http://52.23.74.126:8000/datanodes
```

---

## 6. Cliente CLI en la EC2

```bash
sudo apt install -y python3-pip
cd ~/FinalDFS/client
pip3 install -r requirements.txt

python3 dfs_cli.py register demo demo123
python3 dfs_cli.py login demo demo123
python3 dfs_cli.py status
python3 dfs_cli.py put ../archivo1.txt
python3 dfs_cli.py ls
```

> Ejecutar siempre desde `~/FinalDFS/client`, no desde la raíz del repo.

---

## 7. Actualizar tras cambios en GitHub

```bash
cd ~/FinalDFS
git pull origin main
docker compose up -d --build
docker compose restart datanode1 datanode2 datanode3
```

---

## 8. Solución de problemas

| Síntoma | Causa | Solución |
|---------|--------|----------|
| `no configuration file provided` | No estás en `~/FinalDFS` | `cd ~/FinalDFS` |
| `env file namenode/.env not found` | Falta el archivo | `cp namenode/.env.example namenode/.env` |
| NameNode se reinicia | `MONGO_URI` incorrecto | Revisar `docker compose logs namenode` |
| Todos los nodos `dead` | Sin heartbeat | `docker compose restart datanode1 datanode2 datanode3` |
| `invalid choice: status` | Código viejo | `git reset --hard origin/main` |
| Login con hash bcrypt | Contraseña incorrecta | Usar contraseña en texto plano del `register` |
| `put` sin sesión | Falta login | `python3 dfs_cli.py login ...` primero |

---

## 9. Mapa de puertos

| Puerto host | Contenedor | Servicio |
|-------------|------------|----------|
| 8000 | namenode:8000 | NameNode |
| 8001 | datanode1:8001 | DataNode 1 |
| 8002 | datanode2:8001 | DataNode 2 |
| 8003 | datanode3:8001 | DataNode 3 |

Comunicación interna Docker: `http://namenode:8000`, `http://datanode1:8001`, etc.
