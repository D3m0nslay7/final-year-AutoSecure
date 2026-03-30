"""
Attack Script: Generic IoT Device (mDNS / HTTP)
================================================
Target  : Generic IoT HTTP device discovered via mDNS (_http._tcp.local.)
Default : 127.0.0.1:80

Attacks performed
-----------------
1. PORT SCAN      — connects to 20 ports rapidly
                    → triggers PORT_SCAN alert in monitoring engine
2. HTTP BRUTE     — probes common IoT admin endpoints
                    → demonstrates weak HTTP surface
3. HTTP FLOOD     — sends rapid repeated requests to the device
                    → simulates DoS against the HTTP service

Run order
---------
  1. python Devices/mDNS/generic_iot_device.py   (start the device)
  2. python Engines/main.py                       (start monitoring)
  3. python Attacks/attack_generic_iot.py         (run this script)

Expected monitoring alerts
--------------------------
  [PORT_SCAN]  — more than 10 distinct ports probed within 10 seconds
"""

import socket
import time
import http.client
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Override with:  python attack_generic_iot.py <TARGET_IP> [TARGET_PORT]
# Docker example: python attack_generic_iot.py 172.17.0.2 80
TARGET_IP      = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
TARGET_PORT    = int(sys.argv[2]) if len(sys.argv) > 2 else 80
SCAN_TIMEOUT   = 0.3
FLOOD_REQUESTS = 20
# ─────────────────────────────────────────────────────────────────────────────


def print_banner(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── ATTACK 1: PORT SCAN ───────────────────────────────────────────────────────
def attack_port_scan():
    print_banner("ATTACK 1: Port Scan")
    print(f"  Target : {TARGET_IP}")
    print(f"  Action : Probing 20 ports to trigger PORT_SCAN detection")
    print(f"  Alert  : PORT_SCAN (>10 distinct ports in 10 seconds)\n")

    # Probe a wide set of ports quickly so the monitoring engine fires
    ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 443,
             445, 3306, 3389, 5000, 5900, 8080, 8443, 8883, 9000, 9090]

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

    print(f"\n  Scan complete. Open ports found: {open_ports or 'none'}")
    print("  >> PORT_SCAN alert should have fired in the monitoring engine")


# ── ATTACK 2: HTTP ENDPOINT BRUTE FORCE ──────────────────────────────────────
def attack_http_brute():
    print_banner("ATTACK 2: HTTP Admin Endpoint Brute Force")
    print(f"  Target : http://{TARGET_IP}:{TARGET_PORT}")
    print(f"  Action : Probing common IoT admin paths\n")

    endpoints = [
        "/", "/admin", "/login", "/config", "/setup",
        "/api/v1/status", "/api/v1/config", "/api/v1/credentials",
        "/device", "/device/info", "/firmware", "/update",
        "/cgi-bin/admin", "/.env", "/backup",
    ]

    for path in endpoints:
        try:
            conn = http.client.HTTPConnection(TARGET_IP, TARGET_PORT, timeout=2)
            conn.request("GET", path, headers={"User-Agent": "AttackScript/1.0"})
            resp = conn.getresponse()
            print(f"    GET {path:30s} → {resp.status} {resp.reason}")
            conn.close()
        except ConnectionRefusedError:
            print(f"    GET {path:30s} → Connection refused (device not running?)")
            break
        except Exception as e:
            print(f"    GET {path:30s} → {type(e).__name__}")

    print("\n  >> Brute force complete — check device logs for unexpected 200 responses")


# ── ATTACK 3: HTTP FLOOD ──────────────────────────────────────────────────────
def attack_http_flood():
    print_banner("ATTACK 3: HTTP Request Flood (DoS Simulation)")
    print(f"  Target  : http://{TARGET_IP}:{TARGET_PORT}/")
    print(f"  Action  : Sending {FLOOD_REQUESTS} rapid requests\n")

    success = 0
    failed  = 0

    for i in range(FLOOD_REQUESTS):
        try:
            conn = http.client.HTTPConnection(TARGET_IP, TARGET_PORT, timeout=2)
            conn.request("GET", "/", headers={"User-Agent": f"Flood/{i}"})
            conn.getresponse()
            conn.close()
            success += 1
            print(f"    Request {i+1:3d} : sent", end="\r")
        except Exception:
            failed += 1

    print(f"\n  Flood complete — {success} sent, {failed} failed")
    print("  >> Rapid connections logged by device; monitoring sees traffic spike")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "#" * 60)
    print("#  AutoSecure Attack Simulation — Generic IoT Device      #")
    print("#  Target device : mDNS  _http._tcp.local. (port 80)      #")
    print("#  FOR EDUCATIONAL / LAB USE ONLY                         #")
    print("#" * 60)
    print(f"\n  Target IP   : {TARGET_IP}")
    print(f"  Target Port : {TARGET_PORT}")
    print("\n  Docker: find container IP with:")
    print("    docker inspect --format '{{.NetworkSettings.IPAddress}}' autosecure-mdns-generic-1")
    print("  Or run:  python Attacks/get_docker_ips.py")
    print("\n  Make sure the device and monitoring engine are running first.")
    if "--auto" not in sys.argv:
        input("\n  Press Enter to begin attacks...")

    attack_port_scan()
    time.sleep(1)
    attack_http_brute()
    time.sleep(1)
    attack_http_flood()

    print("\n" + "=" * 60)
    print("  All attacks complete.")
    print("  Check the monitoring engine output for triggered alerts.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
