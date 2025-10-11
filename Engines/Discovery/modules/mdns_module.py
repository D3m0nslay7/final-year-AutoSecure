"""
mDNS Discovery Module - NOT FOR STANDALONE USE
This module is designed to be imported and used by the Discovery Engine only.
"""

# Prevent standalone execution
if __name__ == "__main__":
    raise RuntimeError(
        "This module cannot be run standalone. "
        "Import and use it through the Discovery Engine:\n"
        "  from Engines.Discovery import DiscoveryEngine\n"
        "  engine = DiscoveryEngine()\n"
        "  devices = engine.discover_all()"
    )

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import time
import ipaddress
from typing import Dict, List, Optional


class IoTDeviceListener(ServiceListener):
    """Listener for mDNS/Zeroconf IoT devices"""

    def __init__(self):
        self.devices = {}

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a new service is discovered"""
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
        """Called when a service is removed"""
        _ = zc, type_  # Unused but required by interface
        print(f"\n[DEVICE REMOVED] {name}")
        if name in self.devices:
            del self.devices[name]

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated"""
        info = zc.get_service_info(type_, name)
        if info and name in self.devices:
            device_data = self._parse_device_info(info, type_, name)
            self.devices[name] = device_data
            print(f"\n[DEVICE UPDATED] {name}")

    def _parse_device_info(self, info, type_: str, name: str) -> Dict:
        """Parse service info into structured device data"""
        device_data = {
            'name': name,
            'type': type_,
            'ip_address': None,
            'mac_address': None,
            'port': info.port,
            'server': info.server,
            'properties': {},
            'discovery_method': 'mdns'
        }

        # Extract IP address
        if info.addresses:
            try:
                # Convert bytes to IP address string
                ip_bytes = info.addresses[0]
                if len(ip_bytes) == 4:  # IPv4
                    device_data['ip_address'] = str(ipaddress.IPv4Address(ip_bytes))
                elif len(ip_bytes) == 16:  # IPv6
                    device_data['ip_address'] = str(ipaddress.IPv6Address(ip_bytes))
            except Exception as e:
                print(f"Error parsing IP address: {e}")

        # Extract properties (may contain useful metadata)
        if info.properties:
            try:
                device_data['properties'] = {
                    k.decode('utf-8') if isinstance(k, bytes) else k:
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in info.properties.items()
                }
            except Exception as e:
                print(f"Error parsing properties: {e}")

        # Try to get MAC address from ARP (requires additional logic)
        # Note: MAC address discovery might require OS-specific commands
        if device_data['ip_address']:
            device_data['mac_address'] = self._get_mac_address(device_data['ip_address'])

        return device_data

    def _get_mac_address(self, ip_address: str) -> Optional[str]:
        """
        Attempt to get MAC address for an IP.
        Note: This is a placeholder. Actual implementation would need
        OS-specific ARP table lookups or network scanning.
        """
        _ = ip_address  # Unused for now
        # TODO: Implement MAC address lookup via ARP table
        # This could use:
        # - Windows: 'arp -a' command
        # - Linux/Mac: 'arp -n' or '/proc/net/arp'
        # - Or use scapy library for cross-platform support
        return None

    def get_discovered_devices(self) -> Dict:
        """Return all discovered devices"""
        return self.devices.copy()


class MDNSDiscovery:
    """Main class for mDNS device discovery"""

    def __init__(self, service_types: Optional[List[str]] = None):
        """
        Initialize mDNS discovery

        Args:
            service_types: List of service types to discover
                          Default: ['_http._tcp.local.', '_hap._tcp.local.']
        """
        self.service_types = service_types or [
            '_http._tcp.local.',  # Generic IoT HTTP devices
            '_hap._tcp.local.',   # HomeKit devices
        ]
        self.zeroconf = None
        self.listener = None
        self.browsers = []

    def start_discovery(self, duration: int = 10) -> Dict:
        """
        Start mDNS discovery for specified duration

        Args:
            duration: How long to scan for devices (seconds)

        Returns:
            Dictionary of discovered devices
        """
        try:
            self.zeroconf = Zeroconf()
            self.listener = IoTDeviceListener()

            # Start browsing for each service type
            for service_type in self.service_types:
                browser = ServiceBrowser(self.zeroconf, service_type, self.listener)
                self.browsers.append(browser)

            # Scan for the specified duration
            print(f"Scanning for mDNS devices for {duration} seconds...")
            time.sleep(duration)

            # Return discovered devices
            devices = self.listener.get_discovered_devices()
            print(f"\nFound {len(devices)} mDNS device(s)")

            return devices

        except Exception as e:
            print(f"Error during mDNS discovery: {e}")
            return {}

        finally:
            self.stop_discovery()

    def stop_discovery(self):
        """Stop mDNS discovery and cleanup"""
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None
        self.browsers = []

    def get_current_devices(self) -> Dict:
        """Get currently discovered devices without stopping discovery"""
        if self.listener:
            return self.listener.get_discovered_devices()
        return {}


def discover_mdns_devices(duration: int = 10, service_types: Optional[List[str]] = None) -> Dict:
    """
    Convenience function to discover mDNS devices

    Args:
        duration: How long to scan (seconds)
        service_types: Optional list of service types to discover

    Returns:
        Dictionary of discovered devices with structure:
        {
            'device_name': {
                'name': str,
                'type': str,
                'ip_address': str,
                'mac_address': str or None,
                'port': int,
                'server': str,
                'properties': dict,
                'discovery_method': 'mdns'
            }
        }
    """
    discovery = MDNSDiscovery(service_types)
    return discovery.start_discovery(duration)
