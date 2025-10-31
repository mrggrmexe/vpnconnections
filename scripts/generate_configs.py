#!/usr/bin/env python3
"""
generate_configs.py
-------------------
Генерация WireGuard-конфигов для пользователей VPN-сервиса.
Создаёт приватный/публичный ключ, IP-адрес и файл client.conf.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from ipaddress import ip_network

# ---------------- SETTINGS ----------------
WG_DIR = Path("/etc/wireguard/keys")
CONFIG_DIR = Path("./generated-configs")
NETWORK = ip_network("10.8.0.0/24")
SERVER_ENDPOINT = "vpn.example.com:51820"
SERVER_PUBLIC_KEY = "SERVER_PUBLIC_KEY_PLACEHOLDER"

# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)

# ---------------- UTILITIES ----------------
def generate_keypair() -> tuple[str, str]:
    """Создаёт пару приватный/публичный ключ через wg."""
    private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
    public_key = subprocess.check_output(["wg", "pubkey"], input=private_key.encode()).decode().strip()
    return private_key, public_key

def allocate_ip(used_ips: set[str]) -> str:
    """Находит первый свободный IP из диапазона."""
    for ip in NETWORK.hosts():
        if str(ip) not in used_ips:
            return str(ip)
    raise RuntimeError("Нет свободных IP-адресов в пуле!")

def save_config(user_id: str, private_key: str, vpn_ip: str) -> Path:
    """Создаёт клиентский WireGuard-конфиг."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    content = f"""
[Interface]
PrivateKey = {private_key}
Address = {vpn_ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_ENDPOINT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    path = CONFIG_DIR / f"{user_id}.conf"
    path.write_text(content.strip())
    return path

# ---------------- MAIN ----------------
def main():
    logging.info("=== Генерация конфигов WireGuard ===")
    used_ips = {line.strip() for line in Path("used_ips.txt").read_text().splitlines()} if Path("used_ips.txt").exists() else set()

    user_id = input("Введите user_id или имя пользователя: ").strip()
    private_key, public_key = generate_keypair()
    vpn_ip = allocate_ip(used_ips)

    cfg_path = save_config(user_id, private_key, vpn_ip)
    used_ips.add(vpn_ip)
    Path("used_ips.txt").write_text("\n".join(sorted(used_ips)))

    record = {
        "user_id": user_id,
        "public_key": public_key,
        "vpn_ip": vpn_ip,
        "config_file": str(cfg_path)
    }

    Path(f"{user_id}.json").write_text(json.dumps(record, indent=2))
    logging.info(f"✅ Конфиг создан: {cfg_path}")
    logging.info(f"🔑 Публичный ключ: {public_key}")
    logging.info("Запиши данные в базу backend-а для синхронизации с нодами.")

if __name__ == "__main__":
    main()
