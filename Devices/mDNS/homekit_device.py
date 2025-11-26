from zeroconf import ServiceInfo, Zeroconf
import socket
import time
import os
import random

def get_container_ip():
    """Get the container's IP address"""
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return f"192.168.1.{random.randint(100, 254)}"

def generate_mac():
    """Generate a random MAC-like address"""
    return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])

def broadcast_homekit_device():
    zeroconf = Zeroconf()

    # Get container IP or use environment variable
    container_ip = os.getenv('DEVICE_IP', get_container_ip())
    device_id = os.getenv('DEVICE_ID', str(random.randint(1000, 9999)))
    port = int(os.getenv('DEVICE_PORT', '8080'))
    mac_address = os.getenv('DEVICE_MAC', generate_mac())

    # HomeKit smart light device
    device = ServiceInfo(
        "_hap._tcp.local.",
        f"SmartLight-{device_id}._hap._tcp.local.",
        addresses=[socket.inet_aton(container_ip)],
        port=port,
        properties={
            'md': f'SmartBulb-{device_id}',  # Model
            'pv': '1.0',                       # Protocol version
            'id': mac_address,                 # Device ID (MAC-like)
            'c#': '1',                         # Configuration number
            'sf': '1',                         # Status flags
            'ff': '0',                         # Feature flags
            's#': '1',                         # State number
            'ci': '5'                          # Category identifier (5 = lightbulb)
        }
    )

    zeroconf.register_service(device)
    print(f"Broadcasting HomeKit Device: {device.name}")
    print(f"Device ID: {device_id}")
    print(f"MAC Address: {mac_address}")
    print(f"IP: {container_ip}")
    print(f"Port: {port}")
    print(f"Device Type: Smart Light Bulb")
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
    broadcast_homekit_device()
