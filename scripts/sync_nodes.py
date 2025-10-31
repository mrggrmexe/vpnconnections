#!/usr/bin/env python3
"""
sync_nodes.py
--------------
Синхронизация разрешённых пользователей (пиров)
на всех VPN-ноды через SSH или API.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import List

# ---------------- SETTINGS ----------------
NODES = [
    {"name": "nl1", "host": "vpn-nl1.example.com"},
    {"name": "us1", "host": "vpn-us1.example.com"},
]
REMOTE_WG_CONF = "/etc/wireguard/wg0.conf"
AUTHORIZED_FILE = Path("./authorized_users.json")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

# ---------------- FUNCTIONS ----------------
def load_authorized_users() -> List[dict]:
    """Читает список активных пользователей из JSON (генерируется backend-ом)."""
    if not AUTHORIZED_FILE.exists():
        raise FileNotFoundError("authorized_users.json не найден")
    with open(AUTHORIZED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def build_peer_block(user: dict) -> str:
    """Формирует блок [Peer] для wg-конфига."""
    return f"""
[Peer]
PublicKey = {user['public_key']}
AllowedIPs = {user['vpn_ip']}/32
PersistentKeepalive = 25
"""

def sync_node(node: dict, peers_text: str):
    """Отправляет обновлённый список пиров на ноду через SSH."""
    logging.info(f"🚀 Синхронизация ноды {node['name']} ({node['host']})")
    tmp_path = "/tmp/wg0_peers.conf"
    subprocess.run([
        "ssh", node["host"],
        f"sudo tee {tmp_path} >/dev/null && "
        f"sudo wg syncconf wg0 <(wg-quick strip wg0 && cat {tmp_path}) && "
        f"rm -f {tmp_path}"
    ], input=peers_text.encode(), check=False)
    logging.info(f"Нода {node['name']} обновлена")

# ---------------- MAIN ----------------
def main():
    logging.info("=== Синхронизация VPN-нод ===")
    users = load_authorized_users()
    logging.info(f"Найдено активных пользователей: {len(users)}")

    peers = "\n".join(build_peer_block(u) for u in users)
    for node in NODES:
        sync_node(node, peers)

    logging.info("Синхронизация завершена")

if __name__ == "__main__":
    main()
