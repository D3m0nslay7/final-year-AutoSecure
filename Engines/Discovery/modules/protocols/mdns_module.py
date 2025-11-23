"""
mDNS Discovery Module
"""

# Prevent standalone execution
if __name__ == "__main__":
    raise RuntimeError("This module cannot be run standalone. ")

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import time
import ipaddress
from typing import Dict, List, Optional

# Import ARP enrichment function
try:
    from .arp_module import enrich_devices_with_mac
except ImportError:
    # Fallback for different import contexts
    try:
        from arp_module import enrich_devices_with_mac
    except ImportError:
        enrich_devices_with_mac = None


class IoTDeviceListener(ServiceListener):
    def __init__(self):
        self.devices = {}

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            # Parse device information
            device_data = self._parse_device_info(info, type_, name)
            self.devices[name] = device_data

            print(f"\n[DEVICE DISCOVERED]")
            print(f"Name: {name}")
            print(f"Type: {type_}")
            print(f"IP Address: {device_data.get('ip_address', 'Unknown')}")
            print(f"Port: {device_data.get('port', 'Unknown')}")
            print("-" * 50)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        _ = zc, type_  # Unused parameters
        print(f"\n[DEVICE REMOVED] {name}")
        if name in self.devices:
            del self.devices[name]

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and name in self.devices:
            device_data = self._parse_device_info(info, type_, name)
            self.devices[name] = device_data
            print(f"\n[DEVICE UPDATED] {name}")

    def _parse_device_info(self, info, type_: str, name: str) -> Dict:
        device_data = {
            "name": name,
            "type": type_,
            "ip_address": None,
            "mac_address": None,
            "port": info.port,
            "server": info.server,
            "properties": {},
            "discovery_method": "mdns",
        }
        if info.addresses:
            try:
                ip_bytes = info.addresses[0]
                if len(ip_bytes) == 4:  # IPv4
                    device_data["ip_address"] = str(ipaddress.IPv4Address(ip_bytes))
                elif len(ip_bytes) == 16:  # IPv6
                    device_data["ip_address"] = str(ipaddress.IPv6Address(ip_bytes))
            except Exception as e:
                print(f"Error parsing IP address: {e}")

        if info.properties:
            try:
                device_data["properties"] = {
                    k.decode("utf-8") if isinstance(k, bytes) else k: (
                        v.decode("utf-8") if isinstance(v, bytes) else v
                    )
                    for k, v in info.properties.items()
                }
            except Exception as e:
                print(f"Error parsing properties: {e}")

        if device_data["ip_address"]:
            device_data["mac_address"] = self._get_mac_address(
                device_data["ip_address"]
            )

        return device_data

    def _get_mac_address(self, ip_address: str) -> Optional[str]:
        if not ip_address:
            return None

        if enrich_devices_with_mac is not None:
            try:
                mac_mapping = enrich_devices_with_mac([ip_address], timeout=1)
                return mac_mapping.get(ip_address)
            except Exception:
                # If ARP fails (permissions, network issues), return None
                return None

        return None

    def get_discovered_devices(self) -> Dict:
        return self.devices.copy()


class MDNSDiscovery:

    def __init__(self, service_types: Optional[List[str]] = None):
        self.service_types = service_types or [
            "_http._tcp.local.",  # Generic IoT HTTP devices
            "_hap._tcp.local.",  # HomeKit devices
        ]
        self.zeroconf = None
        self.listener = None
        self.browsers = []

    def start_discovery(self, duration: int = 10) -> Dict:
        try:
            self.zeroconf = Zeroconf()
            self.listener = IoTDeviceListener()
            for service_type in self.service_types:
                browser = ServiceBrowser(self.zeroconf, service_type, self.listener)
                self.browsers.append(browser)

            print(f"Scanning for mDNS devices for {duration} seconds...")
            time.sleep(duration)
            devices = self.listener.get_discovered_devices()
            print(f"\nFound {len(devices)} mDNS device(s)")

            return devices

        except Exception as e:
            print(f"Error during mDNS discovery: {e}")
            return {}

        finally:
            self.stop_discovery()

    def stop_discovery(self):
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None
        self.browsers = []

    def get_current_devices(self) -> Dict:
        if self.listener:
            return self.listener.get_discovered_devices()
        return {}


def discover_mdns_devices(
    duration: int = 10, service_types: Optional[List[str]] = None
) -> Dict:
    discovery = MDNSDiscovery(service_types)
    return discovery.start_discovery(duration)
