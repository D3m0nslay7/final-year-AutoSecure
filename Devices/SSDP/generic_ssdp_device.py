from ssdpy import SSDPServer
import time
import random
import uuid
import socket
import os


def get_container_ip():
    """Get the container's IP address"""
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return f"192.168.1.{random.randint(100, 254)}"


def broadcast_generic_iot():
    # Get container IP or use environment variable
    container_ip = os.getenv('DEVICE_IP', get_container_ip())
    device_id = os.getenv('DEVICE_ID', str(uuid.uuid4())[:8])
    port = int(os.getenv('DEVICE_PORT', str(random.randint(8000, 9000))))

    # Randomized parameters
    usn = f"uuid:{uuid.uuid4()}::urn:schemas-upnp-org:device:Basic:1"

    # Random device type
    device_types = [
        "urn:schemas-upnp-org:device:Basic:1",
        "urn:schemas-upnp-org:device:MediaRenderer:1",
        "urn:schemas-upnp-org:device:MediaServer:1",
        "upnp:rootdevice"
    ]
    device_type = random.choice(device_types)

    location = f"http://{container_ip}:{port}/device.xml"

    print("=" * 60)
    print(f"Broadcasting Generic SSDP Device")
    print("=" * 60)
    print(f"Device ID:    {device_id}")
    print(f"USN:          {usn}")
    print(f"Type:         {device_type}")
    print(f"Location:     {location}")
    print(f"IP Address:   {container_ip}")
    print(f"Port:         {port}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop broadcasting...")

    server = SSDPServer(
        usn,
        device_type=device_type,
        location=location
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nStopping broadcast...")
    finally:
        server.stop()
        print("Device unregistered")


if __name__ == "__main__":
    broadcast_generic_iot()
