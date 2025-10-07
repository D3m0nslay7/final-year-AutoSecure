from zeroconf import ServiceInfo, Zeroconf
import socket
import time

def broadcast_generic_iot():
    zeroconf = Zeroconf()

    # Generic IoT device with HTTP interface
    device = ServiceInfo(
        "_http._tcp.local.",
        "GenericIoTDevice._http._tcp.local.",
        addresses=[socket.inet_aton("192.168.1.100")],
        port=80,
        properties={
            'model': 'IoT-Generic-001',
            'manufacturer': 'Generic IoT Corp',
            'version': '1.0.0',
            'type': 'sensor'
        }
    )

    zeroconf.register_service(device)
    print(f"Broadcasting Generic IoT Device: {device.name}")
    print(f"IP: 192.168.1.100")
    print(f"Port: 80")
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
