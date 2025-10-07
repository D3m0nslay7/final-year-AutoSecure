from zeroconf import ServiceInfo, Zeroconf
import socket
import time

def broadcast_homekit_device():
    zeroconf = Zeroconf()

    # HomeKit smart light device
    device = ServiceInfo(
        "_hap._tcp.local.",
        "SmartLight._hap._tcp.local.",
        addresses=[socket.inet_aton("192.168.1.101")],
        port=8080,
        properties={
            'md': 'SmartBulb',           # Model
            'pv': '1.0',                  # Protocol version
            'id': 'AA:BB:CC:DD:EE:FF',   # Device ID (MAC-like)
            'c#': '1',                    # Configuration number
            'sf': '1',                    # Status flags
            'ff': '0',                    # Feature flags
            's#': '1',                    # State number
            'ci': '5'                     # Category identifier (5 = lightbulb)
        }
    )

    zeroconf.register_service(device)
    print(f"Broadcasting HomeKit Device: {device.name}")
    print(f"IP: 192.168.1.101")
    print(f"Port: 8080")
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
