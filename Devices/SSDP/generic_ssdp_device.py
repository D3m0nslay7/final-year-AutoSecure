from ssdpy import SSDPServer
import time
import random
import uuid


def broadcast_generic_iot():
    # Randomized parameters
    device_id = str(uuid.uuid4())[:8]
    usn = f"uuid:{uuid.uuid4()}::urn:schemas-upnp-org:device:Basic:1"

    # Random IP in test range (192.168.1.100-254)
    random_ip = f"192.168.1.{random.randint(100, 254)}"

    # Random port (8000-9000 range)
    random_port = random.randint(8000, 9000)

    # Random device type
    device_types = [
        "urn:schemas-upnp-org:device:Basic:1",
        "urn:schemas-upnp-org:device:MediaRenderer:1",
        "urn:schemas-upnp-org:device:MediaServer:1",
        "upnp:rootdevice"
    ]
    device_type = random.choice(device_types)

    location = f"http://{random_ip}:{random_port}/device.xml"

    print("=" * 60)
    print(f"Broadcasting Generic SSDP Device")
    print("=" * 60)
    print(f"Device ID:    {device_id}")
    print(f"USN:          {usn}")
    print(f"Type:         {device_type}")
    print(f"Location:     {location}")
    print(f"IP Address:   {random_ip}")
    print(f"Port:         {random_port}")
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
