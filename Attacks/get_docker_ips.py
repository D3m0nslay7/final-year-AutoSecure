"""
Docker Target Discovery Helper
================================
Queries Docker for all running AutoSecure containers and prints their IPs.
Run this first to get the correct IPs to pass to each attack script.

Usage
-----
  python Attacks/get_docker_ips.py

Output example
--------------
  Container                      IP             Attack Command
  ─────────────────────────────────────────────────────────────────────────────────
  autosecure-mdns-generic-1      172.17.0.2     python Attacks/attack_generic_iot.py 172.17.0.2
  autosecure-mdns-homekit-1      172.17.0.4     python Attacks/attack_homekit.py 172.17.0.4
  autosecure-ssdp-generic-1      172.17.0.6     python Attacks/attack_ssdp.py
  autosecure-mqtt-mosquitto-1    172.17.0.8     python Attacks/attack_mosquitto.py 172.17.0.8
  autosecure-mqtt-hivemq-1       172.17.0.9     python Attacks/attack_hivemq.py 172.17.0.9
  autosecure-mqtt-emqx-1         172.17.0.10    python Attacks/attack_emqx.py 172.17.0.10
"""

import subprocess
import json
import sys

# Map container name patterns to their attack script
ATTACK_SCRIPT_MAP = {
    "mdns-generic":   "attack_generic_iot.py {ip}",
    "mdns-homekit":   "attack_homekit.py {ip}",
    "ssdp-generic":   "attack_ssdp.py",           # SSDP uses multicast, no IP arg
    "mqtt-mosquitto": "attack_mosquitto.py {ip}",
    "mqtt-hivemq":    "attack_hivemq.py {ip}",
    "mqtt-emqx":      "attack_emqx.py {ip}",
}


def get_autosecure_containers():
    """Return list of (name, ip) for all running autosecure-* containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=autosecure-",
             "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
    except FileNotFoundError:
        print("ERROR: Docker is not installed or not on PATH.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: Docker command timed out.")
        sys.exit(1)

    names = [n.strip() for n in result.stdout.splitlines() if n.strip()]

    if not names:
        print("No running autosecure-* containers found.")
        print("Start devices first with:  cd Devices && run-all-devices.bat")
        return []

    containers = []
    for name in names:
        ip_result = subprocess.run(
            ["docker", "inspect",
             "--format", "{{.NetworkSettings.IPAddress}}", name],
            capture_output=True, text=True, timeout=5
        )
        ip = ip_result.stdout.strip()
        if not ip:
            # Try networks (custom Docker networks)
            net_result = subprocess.run(
                ["docker", "inspect",
                 "--format",
                 "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                 name],
                capture_output=True, text=True, timeout=5
            )
            ip = net_result.stdout.strip() or "unknown"
        containers.append((name, ip))

    return containers


def get_attack_command(container_name, ip):
    """Return the attack script command for a given container name."""
    for pattern, cmd_template in ATTACK_SCRIPT_MAP.items():
        if pattern in container_name:
            cmd = cmd_template.format(ip=ip)
            return f"python Attacks/{cmd}"
    return "python Attacks/attack_generic_iot.py " + ip


def main():
    print("\n" + "=" * 85)
    print("  AutoSecure — Docker Container IPs")
    print("=" * 85)

    containers = get_autosecure_containers()
    if not containers:
        return

    print(f"\n  {'Container':<35} {'IP':<16} Attack Command")
    print("  " + "─" * 81)

    for name, ip in sorted(containers):
        cmd = get_attack_command(name, ip)
        print(f"  {name:<35} {ip:<16} {cmd}")

    print()

    # Print the ARP spoof note
    print("  NOTE — ARP Spoofing:")
    print("    attack_arp_spoof.py MUST run inside Docker (not from Windows host).")
    print("    Build and run the attack container:")
    print("      docker build -t autosecure-arp-attack -f Attacks/Dockerfile.arp_spoof Attacks/")

    # Suggest a sample run command using first container found
    target_container = next(
        (c for c in containers if "mdns-generic" in c[0] or "mqtt-mosquitto" in c[0]),
        containers[0] if containers else None
    )
    if target_container:
        target_ip  = target_container[1]
        victim_ip  = ".".join(target_ip.split(".")[:3]) + ".1"   # gateway
        print(f"      docker run --rm --network bridge --cap-add=NET_RAW --cap-add=NET_ADMIN \\")
        print(f"        autosecure-arp-attack {target_ip} {victim_ip}")

    print("=" * 85 + "\n")


if __name__ == "__main__":
    main()
