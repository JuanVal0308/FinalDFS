#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
DFS CLI — Cliente unificado para el Sistema de Archivos Distribuido.

Uso:
    python dfs_cli.py <comando> [argumentos]

Comandos:
    register <usuario> <contraseña>   Registra un nuevo usuario
    login    <usuario> <contraseña>   Inicia sesión y guarda el token en .dfs_token
    put      <ruta_local>             Sube un archivo al DFS
    get      <nombre_remoto>          Descarga un archivo del DFS
    ls                                Lista los archivos del usuario
    status                            Muestra el estado de los DataNodes
    rm       <nombre_remoto>          Elimina un archivo del DFS
    mkdir    <ruta>                   Crea un directorio virtual
    rmdir    <ruta>                   Elimina un directorio y su contenido

Variables de entorno:
    NAMENODE_URL      URL del NameNode (default: http://52.23.74.126:8000)
    DFS_BLOCK_SIZE    Tamaño de bloque en bytes (default: 67108864 = 64 MB)
"""

import os
import sys
import math
import hashlib
import tempfile
import argparse
import requests

# ---------------------------------------------------------------------------
# Configuración desde variables de entorno
# ---------------------------------------------------------------------------
NAMENODE_URL = os.getenv("NAMENODE_URL", "http://52.23.74.126:8000")
BLOCK_SIZE   = int(os.getenv("DFS_BLOCK_SIZE", 64 * 1024 * 1024))  # 64 MB por defecto
TOKEN_FILE   = os.path.join(os.path.dirname(__file__), ".dfs_token")


# ---------------------------------------------------------------------------
# Utilidades de token
# ---------------------------------------------------------------------------

def save_token(token: str) -> None:
    with open(TOKEN_FILE, "w") as f:
        f.write(token)


def load_token() -> str:
    if not os.path.exists(TOKEN_FILE):
        print("[ERROR] No hay sesión activa. Ejecuta primero: python dfs_cli.py login <usuario> <contraseña>")
        sys.exit(1)
    with open(TOKEN_FILE, "r") as f:
        return f.read().strip()


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {load_token()}"}


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_register(username: str, password: str) -> None:
    """Registra un nuevo usuario."""
    resp = requests.post(
        f"{NAMENODE_URL}/auth/register",
        json={"username": username, "password": password}
    )
    if resp.status_code == 200:
        print(f"[OK] Usuario '{username}' registrado correctamente.")
    else:
        print(f"[ERROR] {resp.status_code}: {resp.json().get('detail', resp.text)}")
        sys.exit(1)


def cmd_login(username: str, password: str) -> None:
    """Autentica al usuario y guarda el token localmente."""
    resp = requests.post(
        f"{NAMENODE_URL}/auth/login",
        json={"username": username, "password": password}
    )
    if resp.status_code == 200:
        token = resp.json()["token"]
        save_token(token)
        print(f"[OK] Sesión iniciada como '{username}'. Token guardado en {TOKEN_FILE}")
    else:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text or "(sin respuesta del servidor)"
        print(f"[ERROR] {resp.status_code}: {detail}")
        sys.exit(1)


def cmd_put(local_path: str) -> None:
    """
    Sube un archivo al DFS:
    1. Divide el archivo en bloques de DFS_BLOCK_SIZE bytes.
    2. Solicita asignación de bloques al NameNode.
    3. Sube cada bloque a sus réplicas con checksum SHA-256.
    4. Registra la metadata en el NameNode.
    """
    if not os.path.exists(local_path):
        print(f"[ERROR] Archivo no encontrado: {local_path}")
        sys.exit(1)

    filename = os.path.basename(local_path)

    with open(local_path, "rb") as f:
        data = f.read()

    file_size  = len(data)
    num_blocks = max(1, math.ceil(file_size / BLOCK_SIZE))

    print(f"[INFO] Archivo: {filename} ({file_size} bytes) → {num_blocks} bloque(s) de {BLOCK_SIZE} bytes")

    # Solicitar asignación al NameNode
    alloc_resp = requests.get(
        f"{NAMENODE_URL}/files/allocate/{filename}/{num_blocks}",
        headers=auth_headers()
    )
    if alloc_resp.status_code != 200:
        print(f"[ERROR] Allocate falló: {alloc_resp.status_code} {alloc_resp.text}")
        sys.exit(1)

    allocation = alloc_resp.json()
    blocks_metadata = []

    for i in range(num_blocks):
        start  = i * BLOCK_SIZE
        end    = start + BLOCK_SIZE
        chunk  = data[start:end]

        checksum   = hashlib.sha256(chunk).hexdigest()
        block_info = allocation["blocks"][i]
        block_id   = block_info["block_id"]
        replicas   = block_info["replicas"]

        print(f"  Bloque {i}: {block_id} ({len(chunk)} bytes, sha256={checksum[:12]}…)")

        # Subir a cada réplica
        for replica_url in replicas:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(chunk)
                tmp_path = tmp.name

            try:
                with open(tmp_path, "rb") as f:
                    upload = requests.post(
                        f"{replica_url}/block/upload/{block_id}",
                        files={"file": f},
                        timeout=30
                    )
                if upload.status_code == 200:
                    print(f"    ✓ Réplica: {replica_url}")
                else:
                    print(f"    ✗ Error en {replica_url}: {upload.status_code}")
            except Exception as e:
                print(f"    ✗ Excepción en {replica_url}: {e}")
            finally:
                os.unlink(tmp_path)

        blocks_metadata.append({
            "block_id":   block_id,
            "replicas":   replicas,
            "checksum":   checksum,
            "size_bytes": len(chunk)
        })

    # Registrar metadata en el NameNode
    metadata = {
        "filename":   filename,
        "blocks":     blocks_metadata,
        "total_size": file_size
    }

    reg_resp = requests.post(
        f"{NAMENODE_URL}/files/register",
        json=metadata,
        headers=auth_headers()
    )
    if reg_resp.status_code == 200:
        print(f"[OK] Archivo '{filename}' registrado en el DFS.")
    else:
        print(f"[ERROR] Register falló: {reg_resp.status_code} {reg_resp.text}")
        sys.exit(1)


def cmd_get(filename: str) -> None:
    """
    Descarga un archivo del DFS:
    1. Obtiene la metadata del NameNode.
    2. Descarga cada bloque intentando réplicas en orden.
    3. Verifica el checksum SHA-256 si está disponible.
    4. Reconstruye el archivo localmente como downloaded_<filename>.
    """
    meta_resp = requests.get(
        f"{NAMENODE_URL}/files/{filename}",
        headers=auth_headers()
    )
    if meta_resp.status_code == 404:
        print(f"[ERROR] Archivo '{filename}' no encontrado en el DFS.")
        sys.exit(1)
    elif meta_resp.status_code != 200:
        print(f"[ERROR] Metadata falló: {meta_resp.status_code} {meta_resp.text}")
        sys.exit(1)

    metadata  = meta_resp.json()
    blocks    = metadata["blocks"]
    out_path  = f"downloaded_{filename}"

    print(f"[INFO] Descargando '{filename}' → '{out_path}' ({len(blocks)} bloque(s))")

    with open(out_path, "wb") as outfile:
        for block in blocks:
            block_id       = block["block_id"]
            replicas       = block["replicas"]
            expected_chk   = block.get("checksum")
            downloaded     = False

            for replica_url in replicas:
                try:
                    print(f"  Intentando {block_id} desde {replica_url} …")
                    resp = requests.get(
                        f"{replica_url}/block/{block_id}",
                        timeout=10
                    )
                    if resp.status_code == 200:
                        chunk = resp.content

                        # Verificar checksum si está disponible
                        if expected_chk:
                            actual_chk = hashlib.sha256(chunk).hexdigest()
                            if actual_chk != expected_chk:
                                print(f"    ✗ Checksum inválido en {replica_url}. Intentando otra réplica…")
                                continue

                        outfile.write(chunk)
                        print(f"    ✓ OK ({len(chunk)} bytes)")
                        downloaded = True
                        break
                    else:
                        print(f"    ✗ {replica_url} respondió {resp.status_code}")
                except Exception as e:
                    print(f"    ✗ Excepción en {replica_url}: {e}")

            if not downloaded:
                print(f"[ERROR] Todas las réplicas fallaron para bloque: {block_id}")
                sys.exit(1)

    print(f"[OK] Archivo reconstruido: {out_path}")


def cmd_status() -> None:
    """Muestra el estado de cada DataNode registrado en el NameNode."""
    resp = requests.get(f"{NAMENODE_URL}/datanodes", timeout=10)
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text or "(sin respuesta)"
        print(f"[ERROR] {resp.status_code}: {detail}")
        sys.exit(1)

    nodes = resp.json().get("datanodes", [])
    if not nodes:
        print("(no hay DataNodes registrados)")
        return

    print(f"{'Nodo':<12} {'Estado':<8} {'Bloques':>8}  {'Último heartbeat':<22} URL")
    print("-" * 90)
    for n in nodes:
        status = n.get("status", "?")
        marker = "✓" if status == "alive" else "✗"
        print(
            f"{n.get('node_id', '?'):<12} "
            f"{marker} {status:<6} "
            f"{n.get('blocks_count', 0):>8}  "
            f"{n.get('last_seen', '—'):<22} "
            f"{n.get('url', '')}"
        )


def cmd_ls() -> None:
    """Lista todos los archivos del usuario autenticado."""
    resp = requests.get(
        f"{NAMENODE_URL}/files",
        headers=auth_headers()
    )
    if resp.status_code != 200:
        print(f"[ERROR] {resp.status_code}: {resp.text}")
        sys.exit(1)

    files = resp.json().get("files", [])
    if not files:
        print("(no hay archivos)")
        return

    print(f"{'Archivo':<40} {'Tamaño':>12}")
    print("-" * 54)
    for f in files:
        size = f.get("total_size")
        size_str = f"{size:,} bytes" if size is not None else "—"
        print(f"{f['filename']:<40} {size_str:>12}")


def cmd_rm(filename: str) -> None:
    """Elimina un archivo del DFS (bloques + metadata)."""
    resp = requests.delete(
        f"{NAMENODE_URL}/files/{filename}",
        headers=auth_headers()
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"[OK] Archivo '{filename}' eliminado del DFS.")
        if result.get("block_errors"):
            print(f"[WARN] Errores al eliminar algunos bloques: {result['block_errors']}")
    elif resp.status_code == 404:
        print(f"[ERROR] Archivo '{filename}' no encontrado.")
        sys.exit(1)
    else:
        print(f"[ERROR] {resp.status_code}: {resp.text}")
        sys.exit(1)


def cmd_mkdir(path: str) -> None:
    """Crea un directorio virtual en el DFS."""
    resp = requests.post(
        f"{NAMENODE_URL}/directories",
        json={"path": path},
        headers=auth_headers()
    )
    if resp.status_code == 200:
        print(f"[OK] Directorio '{path}' creado.")
    elif resp.status_code == 409:
        print(f"[ERROR] El directorio '{path}' ya existe.")
        sys.exit(1)
    else:
        print(f"[ERROR] {resp.status_code}: {resp.text}")
        sys.exit(1)


def cmd_rmdir(path: str) -> None:
    """Elimina un directorio y todos sus archivos del DFS."""
    resp = requests.delete(
        f"{NAMENODE_URL}/directories/{path}",
        headers=auth_headers()
    )
    if resp.status_code == 200:
        result = resp.json()
        deleted = result.get("deleted_files", [])
        print(f"[OK] Directorio '{path}' eliminado.")
        if deleted:
            print(f"     Archivos eliminados: {', '.join(deleted)}")
    elif resp.status_code == 404:
        print(f"[ERROR] Directorio '{path}' no encontrado.")
        sys.exit(1)
    else:
        print(f"[ERROR] {resp.status_code}: {resp.text}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DFS CLI — Sistema de Archivos Distribuido",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # register
    p = subparsers.add_parser("register", help="Registra un nuevo usuario")
    p.add_argument("username")
    p.add_argument("password")

    # login
    p = subparsers.add_parser("login", help="Inicia sesión")
    p.add_argument("username")
    p.add_argument("password")

    # put
    p = subparsers.add_parser("put", help="Sube un archivo al DFS")
    p.add_argument("local_path", help="Ruta local del archivo a subir")

    # get
    p = subparsers.add_parser("get", help="Descarga un archivo del DFS")
    p.add_argument("filename", help="Nombre del archivo en el DFS")

    # ls
    subparsers.add_parser("ls", help="Lista los archivos del usuario")

    # status
    subparsers.add_parser("status", help="Estado de los DataNodes (heartbeat)")

    # rm
    p = subparsers.add_parser("rm", help="Elimina un archivo del DFS")
    p.add_argument("filename", help="Nombre del archivo en el DFS")

    # mkdir
    p = subparsers.add_parser("mkdir", help="Crea un directorio virtual")
    p.add_argument("path", help="Ruta del directorio a crear")

    # rmdir
    p = subparsers.add_parser("rmdir", help="Elimina un directorio y su contenido")
    p.add_argument("path", help="Ruta del directorio a eliminar")

    args = parser.parse_args()

    commands = {
        "register": lambda: cmd_register(args.username, args.password),
        "login":    lambda: cmd_login(args.username, args.password),
        "put":      lambda: cmd_put(args.local_path),
        "get":      lambda: cmd_get(args.filename),
        "ls":       lambda: cmd_ls(),
        "status":   lambda: cmd_status(),
        "rm":       lambda: cmd_rm(args.filename),
        "mkdir":    lambda: cmd_mkdir(args.path),
        "rmdir":    lambda: cmd_rmdir(args.path),
    }

    commands[args.command]()


if __name__ == "__main__":
    main()
