"""
AutoSecure Attack Orchestrator
================================
Runs all attack scripts sequentially against the running device containers.
Designed to execute DURING the monitoring engine's 60-second sniff window
so that every attack is detected and appears in the monitoring summary.

Target IPs are read from environment variables (set by the bat files):
  MDNS_GENERIC_IP    — Generic IoT mDNS device (e.g. 172.17.0.2)
  MDNS_HOMEKIT_IP    — HomeKit mDNS device     (e.g. 172.17.0.4)
  MOSQUITTO_IP       — Mosquitto broker         (e.g. 172.17.0.8)
  HIVEMQ_IP          — HiveMQ broker            (e.g. 172.17.0.9)
  EMQX_IP            — EMQX broker              (e.g. 172.17.0.10)

SSDP attacks use multicast so no IP is needed.

Usage (from the bat files — runs inside Docker):
  docker run --rm --network bridge \\
    -e MDNS_GENERIC_IP=172.17.0.2 ... \\
    autosecure-attacks
"""

import os
import subprocess
import sys
import time

# ── Read target IPs from environment ─────────────────────────────────────────
MDNS_GENERIC_IP = os.environ.get("MDNS_GENERIC_IP", "")
MDNS_HOMEKIT_IP = os.environ.get("MDNS_HOMEKIT_IP", "")
MOSQUITTO_IP    = os.environ.get("MOSQUITTO_IP",    "")
HIVEMQ_IP       = os.environ.get("HIVEMQ_IP",       "")
EMQX_IP         = os.environ.get("EMQX_IP",         "")

# ─────────────────────────────────────────────────────────────────────────────

SEPARATOR = "=" * 65


def run_attack(script, *args):
    """Run a single attack script and stream its output."""
    cmd = ["python", "-u", script] + list(args) + ["--auto"]
    print(f"\n  >> Launching: {' '.join(cmd)}")
    print(SEPARATOR)
    result = subprocess.run(cmd, capture_output=False)
    print(SEPARATOR)
    return result.returncode


def main():
    print("\n" + "#" * 65)
    print("#  AutoSecure — Full Attack Suite                            #")
    print("#  Running all attacks against live Docker containers        #")
    print("#  FOR EDUCATIONAL / LAB USE ONLY                           #")
    print("#" * 65)
    print()
    print("  Target IPs received from environment:")
    print(f"    mDNS Generic  : {MDNS_GENERIC_IP or '(not set — skipping)'}")
    print(f"    mDNS HomeKit  : {MDNS_HOMEKIT_IP or '(not set — skipping)'}")
    print(f"    Mosquitto     : {MOSQUITTO_IP    or '(not set — skipping)'}")
    print(f"    HiveMQ        : {HIVEMQ_IP       or '(not set — skipping)'}")
    print(f"    EMQX          : {EMQX_IP         or '(not set — skipping)'}")
    print()
    print("  These attacks run during the monitoring engine's sniff window.")
    print("  Check the monitoring container logs when done for alerts.\n")
    print(SEPARATOR)

    results = {}

    # ── 1. Generic IoT Device ─────────────────────────────────────────────────
    if MDNS_GENERIC_IP:
        print(f"\n[1/6] Attacking Generic IoT Device  ({MDNS_GENERIC_IP}:80)")
        rc = run_attack("attack_generic_iot.py", MDNS_GENERIC_IP, "80")
        results["Generic IoT"] = rc
        time.sleep(2)
    else:
        print("\n[1/6] Generic IoT Device — skipped (MDNS_GENERIC_IP not set)")

    # ── 2. HomeKit Device ─────────────────────────────────────────────────────
    if MDNS_HOMEKIT_IP:
        print(f"\n[2/6] Attacking HomeKit Device  ({MDNS_HOMEKIT_IP}:8080)")
        rc = run_attack("attack_homekit.py", MDNS_HOMEKIT_IP, "8080")
        results["HomeKit"] = rc
        time.sleep(2)
    else:
        print("\n[2/6] HomeKit Device — skipped (MDNS_HOMEKIT_IP not set)")

    # ── 3. SSDP Device ───────────────────────────────────────────────────────
    print("\n[3/6] Attacking SSDP Device  (multicast — no IP needed)")
    rc = run_attack("attack_ssdp.py")
    results["SSDP"] = rc
    time.sleep(2)

    # ── 4. Mosquitto Broker ───────────────────────────────────────────────────
    if MOSQUITTO_IP:
        print(f"\n[4/6] Attacking Mosquitto Broker  ({MOSQUITTO_IP}:1883)")
        rc = run_attack("attack_mosquitto.py", MOSQUITTO_IP, "1883")
        results["Mosquitto"] = rc
        time.sleep(2)
    else:
        print("\n[4/6] Mosquitto — skipped (MOSQUITTO_IP not set)")

    # ── 5. HiveMQ Broker ─────────────────────────────────────────────────────
    if HIVEMQ_IP:
        print(f"\n[5/6] Attacking HiveMQ Broker  ({HIVEMQ_IP}:8883 + 8000)")
        rc = run_attack("attack_hivemq.py", HIVEMQ_IP, "8883", "8000")
        results["HiveMQ"] = rc
        time.sleep(2)
    else:
        print("\n[5/6] HiveMQ — skipped (HIVEMQ_IP not set)")

    # ── 6. EMQX Broker ───────────────────────────────────────────────────────
    if EMQX_IP:
        print(f"\n[6/6] Attacking EMQX Broker  ({EMQX_IP}:8884 + 18083)")
        rc = run_attack("attack_emqx.py", EMQX_IP, "8884", "18083")
        results["EMQX"] = rc
        time.sleep(2)
    else:
        print("\n[6/6] EMQX — skipped (EMQX_IP not set)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n\n" + "#" * 65)
    print("#  Attack Suite Complete                                      #")
    print("#" * 65)
    print()
    print("  Results:")
    for name, rc in results.items():
        status = "OK" if rc == 0 else f"exit {rc}"
        print(f"    {name:20s} : {status}")

    print()
    print("  Expected monitoring alerts triggered:")
    print("    [PORT_SCAN]        — Generic IoT, HomeKit, HiveMQ, EMQX port scans")
    print("    [UNENCRYPTED_MQTT] — Mosquitto connection on port 1883")
    print()
    print("  To see detected alerts, check the monitoring engine container:")
    print("    docker logs autosecure-engines-run")
    print()


if __name__ == "__main__":
    main()
