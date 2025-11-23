"""
SSDP Discovery Module - NOT FOR STANDALONE USE
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

from ssdpy import SSDPClient
import time
from typing import Dict, List, Optional
import re

# Import ARP enrichment function
try:
    from .arp_module import enrich_devices_with_mac
except ImportError:
    # Fallback for different import contexts
    try:
        from arp_module import enrich_devices_with_mac
    except ImportError:
        enrich_devices_with_mac = None


class SSDPDiscovery:
    """Main class for SSDP/UPnP device discovery"""

    def __init__(self, search_targets: Optional[List[str]] = None):
        """
        Initialize SSDP discovery

        Args:
            search_targets: List of search targets to discover
                          Default: ['ssdp:all']
                          Common targets:
                            - 'ssdp:all' (all SSDP devices)
                            - 'upnp:rootdevice' (UPnP root devices)
                            - 'urn:schemas-upnp-org:device:Basic:1'
        """
        self.search_targets = search_targets or ['ssdp:all']
        self.client = None
        self.devices = {}

    def start_discovery(self, duration: int = 10, mx: int = 2) -> Dict:
        """
        Start SSDP discovery for specified duration

        Args:
            duration: How long to scan for devices (seconds)
            mx: Maximum wait time for device responses (seconds)

        Returns:
            Dictionary of discovered devices
        """
        try:
            self.client = SSDPClient()
            self.devices = {}

            print(f"Scanning for SSDP devices for {duration} seconds...")

            # Perform M-SEARCH for each target
            for search_target in self.search_targets:
                print(f"  Searching for: {search_target}")
                # Note: ssdpy's m_search only accepts st and mx parameters
                responses = self.client.m_search(
                    st=search_target,
                    mx=duration  # Use duration as mx since there's no separate timeout
                )

                # Parse and store responses
                for response in responses:
                    device_data = self._parse_device_info(response)
                    device_id = device_data.get('usn', device_data.get('location', 'unknown'))

                    # Avoid duplicates
                    if device_id not in self.devices:
                        self.devices[device_id] = device_data

                        print(f"\n[DEVICE DISCOVERED]")
                        print(f"Name: {device_data.get('name', 'Unknown')}")
                        print(f"Type: {device_data.get('type', 'Unknown')}")
                        print(f"Location: {device_data.get('location', 'Unknown')}")
                        print(f"IP Address: {device_data.get('ip_address', 'Unknown')}")
                        print("-" * 50)

            # Return discovered devices
            print(f"\nFound {len(self.devices)} SSDP device(s)")
            return self.devices

        except Exception as e:
            print(f"Error during SSDP discovery: {e}")
            return {}

    def _parse_device_info(self, response: Dict) -> Dict:
        """Parse SSDP response into structured device data"""
        device_data = {
            'name': None,
            'type': None,
            'ip_address': None,
            'mac_address': None,
            'port': None,
            'server': None,
            'location': None,
            'usn': None,
            'properties': {},
            'discovery_method': 'ssdp'
        }

        # Extract USN (Unique Service Name)
        if 'usn' in response:
            device_data['usn'] = response['usn']
            # Try to extract a friendly name from USN
            device_data['name'] = self._extract_name_from_usn(response['usn'])

        # Extract location (URL to device description)
        if 'location' in response:
            device_data['location'] = response['location']
            # Extract IP and port from location URL
            ip_port = self._extract_ip_port_from_url(response['location'])
            if ip_port:
                device_data['ip_address'] = ip_port['ip']
                device_data['port'] = ip_port['port']

        # Extract device type
        if 'st' in response:
            device_data['type'] = response['st']

        # Extract server information
        if 'server' in response:
            device_data['server'] = response['server']

        # Store all other response headers as properties
        for key, value in response.items():
            if key.lower() not in ['usn', 'location', 'st', 'server']:
                device_data['properties'][key] = value

        # Try to get MAC address (placeholder for now)
        if device_data['ip_address']:
            device_data['mac_address'] = self._get_mac_address(device_data['ip_address'])

        return device_data

    def _extract_name_from_usn(self, usn: str) -> str:
        """Extract a readable name from USN"""
        # USN format: uuid:device-UUID::urn:schemas-upnp-org:device:deviceType:ver
        # or uuid:device-UUID::upnp:rootdevice
        if '::' in usn:
            parts = usn.split('::')
            if len(parts) >= 2:
                # Return the device type part
                return parts[-1]
        return usn

    def _extract_ip_port_from_url(self, url: str) -> Optional[Dict]:
        """Extract IP address and port from location URL"""
        try:
            # URL format: http://192.168.1.100:8080/description.xml
            match = re.match(r'https?://([^:]+):?(\d+)?', url)
            if match:
                ip = match.group(1)
                port = int(match.group(2)) if match.group(2) else (443 if url.startswith('https') else 80)
                return {'ip': ip, 'port': port}
        except Exception as e:
            print(f"Error parsing URL: {e}")
        return None

    def _get_mac_address(self, ip_address: str) -> Optional[str]:
        """
        Attempt to get MAC address for an IP using ARP.

        Uses the enrich_devices_with_mac function from arp_module
        to query the MAC address via ARP protocol.

        Args:
            ip_address: IP address to lookup

        Returns:
            MAC address if found, None otherwise
        """
        if not ip_address:
            return None

        # Use ARP enrichment function if available
        if enrich_devices_with_mac is not None:
            try:
                mac_mapping = enrich_devices_with_mac([ip_address], timeout=1)
                return mac_mapping.get(ip_address)
            except Exception:
                # If ARP fails (permissions, network issues), return None
                return None

        return None

    def get_discovered_devices(self) -> Dict:
        """Return all discovered devices"""
        return self.devices.copy()


def discover_ssdp_devices(duration: int = 10, search_targets: Optional[List[str]] = None, mx: int = 2) -> Dict:
    """
    Convenience function to discover SSDP devices

    Args:
        duration: How long to scan (seconds)
        search_targets: Optional list of search targets to discover
        mx: Maximum wait time for device responses (seconds)

    Returns:
        Dictionary of discovered devices with structure:
        {
            'device_identifier': {
                'name': str,
                'type': str,
                'ip_address': str,
                'mac_address': str or None,
                'port': int,
                'server': str,
                'location': str,
                'usn': str,
                'properties': dict,
                'discovery_method': 'ssdp'
            }
        }
    """
    discovery = SSDPDiscovery(search_targets)
    return discovery.start_discovery(duration, mx)
