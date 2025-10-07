from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import time

class IoTDeviceListener(ServiceListener):
    def __init__(self):
        self.devices = {}

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            print(f"\n[DEVICE DISCOVERED]")
            print(f"Name: {name}")
            print(f"Type: {type_}")
            print(f"Address: {'.'.join(map(str, info.addresses[0]))}") if info.addresses else print("Address: Unknown")
            print(f"Port: {info.port}")
            print(f"Properties: {info.properties}")
            print(f"Server: {info.server}")
            print("-" * 50)
            self.devices[name] = info

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"\n[DEVICE REMOVED]")
        print(f"Name: {name}")
        print(f"Type: {type_}")
        print("-" * 50)
        if name in self.devices:
            del self.devices[name]

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"\n[DEVICE UPDATED]")
        print(f"Name: {name}")
        print(f"Type: {type_}")
        print("-" * 50)

def main():
    zeroconf = Zeroconf()
    listener = IoTDeviceListener()

    # Browse for both HTTP (generic IoT) and HAP (HomeKit) services
    print("Starting IoT Device Discovery...")
    print("Listening for:")
    print("  - Generic IoT devices (_http._tcp.local.)")
    print("  - HomeKit devices (_hap._tcp.local.)")
    print("=" * 50)

    browser_http = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)
    browser_hap = ServiceBrowser(zeroconf, "_hap._tcp.local.", listener)

    try:
        print("\nScanning for devices... Press Ctrl+C to stop\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping discovery...")
        print(f"\nTotal devices found: {len(listener.devices)}")
    finally:
        zeroconf.close()

if __name__ == "__main__":
    main()
