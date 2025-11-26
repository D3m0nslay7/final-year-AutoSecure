from zeroconf import ServiceInfo, Zeroconf
import socket
import time
import os
import random

def get_container_ip():
    """Get the container's IP address"""
    try:
        # Get hostname
        hostname = socket.gethostname()
        # Get IP address
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        # Fallback to a random IP in test range
        return f"192.168.1.{random.randint(100, 254)}"

def broadcast_generic_iot():
    zeroconf = Zeroconf()

    # Get container IP or use environment variable
    container_ip = os.getenv('DEVICE_IP', get_container_ip())
    device_id = os.getenv('DEVICE_ID', str(random.randint(1000, 9999)))
    port = int(os.getenv('DEVICE_PORT', '80'))

    # Generic IoT device with HTTP interface
    device = ServiceInfo(
        "_http._tcp.local.",
        f"GenericIoTDevice-{device_id}._http._tcp.local.",
        addresses=[socket.inet_aton(container_ip)],
        port=port,
        properties={
            'model': f'IoT-Generic-{device_id}',
            'manufacturer': 'Generic IoT Corp',
            'version': '1.0.0',
            'type': 'sensor',
            'id': device_id
        }
    )

    zeroconf.register_service(device)
    print(f"Broadcasting Generic IoT Device: {device.name}")
    print(f"Device ID: {device_id}")
    print(f"IP: {container_ip}")
    print(f"Port: {port}")
    print(f"Properties: {device.properties}")
    print("\nPress Ctrl+C to stop broadcasting...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping broadcast...")
    finally:
        zeroconf.unregister_service(device)
        zeroconf.close()
        print("Device unregistered")

if __name__ == "__main__":
    broadcast_generic_iot()
