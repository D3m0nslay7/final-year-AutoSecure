"""
AutoSecure Metrics Evaluation
==============================
Runs inside the engines Docker container (same environment as main.py).
Driven by run-evaluate.bat which handles spinning up devices and this container.

This script:
  1. Runs discovery + segmentation (same as main.py)
  2. Starts a background thread that fires the attacks Docker container
     and records the exact wall-clock time each attack category launches
  3. Runs the monitoring engine for 90 seconds
  4. Computes and prints two metrics:

Metric 1 — Time to Detection (TTD)
    Seconds between each attack category being launched and the first
    alert of that type being raised by the monitoring engine.

Metric 2 — Threat Detection Rate (TDR)
    Percentage of expected alert categories that fired at least once.

Device IPs are passed in via environment variables (set by run-evaluate.bat):
    MDNS_GENERIC_IP, MDNS_HOMEKIT_IP, MOSQUITTO_IP, HIVEMQ_IP, EMQX_IP
"""

import os
import sys
import json
import time
import threading
import subprocess

sys.path.insert(0, "/app")

from Discovery import DiscoveryEngine
from Segmentation.segmentation_engine import SegmentationEngine
from Monitoring.monitoring_engine import MonitoringEngine


MONITORING_DURATION = 90

# Which alert type each attack category is expected to trigger
ATTACK_TO_ALERT = {
    "PORT_SCAN":        "PORT_SCAN",
    "UNENCRYPTED_MQTT": "UNENCRYPTED_MQTT",
}


def _resolve_ip(container_name):
    """Ask Docker for the autosecure-net IP of a container."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format",
             "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
             container_name],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _run_attacks(attack_start_times):
    """
    Resolve device IPs from inside the container, then fire the attacks
    Docker container. Records a start timestamp just before each attack
    category launches. Runs in a background thread.
    """
    mdns_generic = _resolve_ip("autosecure-mdns-generic-1")
    mdns_homekit = _resolve_ip("autosecure-mdns-homekit-1")
    mosquitto    = _resolve_ip("autosecure-mqtt-mosquitto-1")
    hivemq       = _resolve_ip("autosecure-mqtt-hivemq-1")
    emqx         = _resolve_ip("autosecure-mqtt-emqx-1")

    print(f"  [eval] Resolved attack targets:")
    print(f"           mDNS Generic : {mdns_generic or '(not found)'}")
    print(f"           mDNS HomeKit : {mdns_homekit or '(not found)'}")
    print(f"           Mosquitto    : {mosquitto    or '(not found)'}")
    print(f"           HiveMQ       : {hivemq       or '(not found)'}")
    print(f"           EMQX         : {emqx         or '(not found)'}")

    # Record start time for all attack categories at container launch.
    # PORT_SCAN fires immediately; UNENCRYPTED_MQTT fires ~20s in but the
    # monitoring engine can see port 1883 traffic from any device, so we
    # timestamp both from container start and let the measured alert time
    # give us the true elapsed detection window.
    t_start = time.time()
    if mdns_generic or mdns_homekit or hivemq or emqx:
        attack_start_times["PORT_SCAN"] = t_start
        print(f"  [eval] Port scan attack start recorded at {time.strftime('%H:%M:%S')}")
    if mosquitto or hivemq or emqx:
        attack_start_times["UNENCRYPTED_MQTT"] = t_start
        print(f"  [eval] MQTT attack start recorded at {time.strftime('%H:%M:%S')}")

    cmd = [
        "docker", "run", "--rm",
        "--name", "autosecure-attacks-eval",
        "--network", "autosecure-net",
        "-e", f"MDNS_GENERIC_IP={mdns_generic}",
        "-e", f"MDNS_HOMEKIT_IP={mdns_homekit}",
        "-e", f"MOSQUITTO_IP={mosquitto}",
        "-e", f"HIVEMQ_IP={hivemq}",
        "-e", f"EMQX_IP={emqx}",
        "autosecure-attacks",
    ]
    print(f"  [eval] Launching attack container at {time.strftime('%H:%M:%S')}")
    subprocess.run(cmd, capture_output=False, timeout=120)
    print(f"  [eval] Attack container finished at {time.strftime('%H:%M:%S')}")


def _compute_ttd(attack_start_times, alerts):
    earliest = {}
    for alert in alerts:
        atype = alert["type"]
        t = alert["raw_time"]
        if atype not in earliest or t < earliest[atype]:
            earliest[atype] = t

    ttd = {}
    for attack_key, alert_type in ATTACK_TO_ALERT.items():
        start = attack_start_times.get(attack_key)
        alert_time = earliest.get(alert_type)
        if start and alert_time:
            ttd[alert_type] = round(alert_time - start, 2)
        elif alert_time:
            ttd[alert_type] = None
    return ttd


def _compute_tdr(attack_start_times, alerts):
    detected = {a["type"] for a in alerts}
    # Only score categories where we actually recorded an attack start
    expected = {
        alert_type
        for attack_key, alert_type in ATTACK_TO_ALERT.items()
        if attack_key in attack_start_times
    }
    if not expected:
        return 0.0, set(), set()
    caught = expected & detected
    missed = expected - detected
    rate = round(len(caught) / len(expected) * 100, 1)
    return rate, caught, missed


def _print_report(ttd, tdr_rate, caught, missed, alerts, elapsed):
    sep = "=" * 62
    print("\n" + sep)
    print("  AutoSecure — Evaluation Report")
    print(sep)

    print("\n  METRIC 1 — Time to Detection (TTD)")
    if ttd:
        for atype, val in sorted(ttd.items()):
            if val is not None:
                print(f"    {atype:25s}  {val:6.2f}s")
            else:
                print(f"    {atype:25s}  (alert fired; start time unavailable)")
        timed = [v for v in ttd.values() if v is not None]
        if timed:
            print(f"\n    Average TTD : {round(sum(timed)/len(timed), 2)}s")
    else:
        print("    No alerts detected — TTD cannot be computed.")
    print("\n  Without AutoSecure: no automated detection (TTD = infinite).")

    total_expected = len(caught) + len(missed)
    print(f"\n  METRIC 2 — Threat Detection Rate (TDR)")
    print(f"    Detected : {len(caught)}/{total_expected} expected alert categories")
    print(f"    TDR      : {tdr_rate}%")
    if caught:
        print(f"    Caught   : {', '.join(sorted(caught))}")
    if missed:
        print(f"    Missed   : {', '.join(sorted(missed))}")
    print("\n  Without AutoSecure: 0% — no detection mechanism exists.")

    print(f"\n  Total alerts raised : {len(alerts)}")
    print(f"  Monitoring window   : {elapsed}s")
    print("\n" + sep + "\n")


def _save_results(ttd, tdr_rate, caught, missed, alerts, elapsed):
    timed = [v for v in ttd.values() if v is not None]
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metric_1_ttd": {
            "per_alert_type_seconds": ttd,
            "average_seconds": round(sum(timed) / len(timed), 2) if timed else None,
            "without_autosecure": "infinite — no automated detection",
        },
        "metric_2_tdr": {
            "rate_percent": tdr_rate,
            "caught": sorted(caught),
            "missed": sorted(missed),
            "without_autosecure": "0%",
        },
        "raw_alerts": alerts,
        "monitoring_window_seconds": elapsed,
    }
    out = os.path.join(os.path.dirname(__file__), "results.json")
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Results saved to: {out}")


def main():
    print("\n" + "#" * 62)
    print("#  AutoSecure — Metrics Evaluation                          #")
    print("#  Metric 1: Time to Detection  |  Metric 2: Detection Rate #")
    print("#" * 62 + "\n")

    print("Phase 1: Discovering devices...")
    devices = DiscoveryEngine().discover_all()
    if not devices:
        print("\n  ERROR: No devices discovered. Are the device containers running?")
        sys.exit(1)

    print("\nPhase 2: Segmenting devices...")
    segmentation = SegmentationEngine()
    for device in devices.values():
        segmentation.apply_segmentation(device)

    print(f"\nPhase 3: Monitoring for {MONITORING_DURATION}s (attacks fire after 5s)...\n")

    monitoring = MonitoringEngine(devices, segmentation.device_segments)
    attack_start_times = {}

    def delayed_attacks():
        time.sleep(5)
        _run_attacks(attack_start_times)

    attack_thread = threading.Thread(target=delayed_attacks, daemon=True)
    attack_thread.start()

    t0 = time.time()
    monitoring.start(duration=MONITORING_DURATION)
    elapsed = round(time.time() - t0, 1)

    attack_thread.join(timeout=15)

    alerts = monitoring.alerts
    ttd = _compute_ttd(attack_start_times, alerts)
    tdr_rate, caught, missed = _compute_tdr(attack_start_times, alerts)

    _print_report(ttd, tdr_rate, caught, missed, alerts, elapsed)
    _save_results(ttd, tdr_rate, caught, missed, alerts, elapsed)


if __name__ == "__main__":
    main()
