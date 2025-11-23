"""
SSDP Discovery Module
"""

if __name__ == "__main__":
    raise RuntimeError("This module cannot be run standalone. ")

from ssdpy import SSDPClient
import time
from typing import Dict, List, Optional
import re

try:
    from .arp_module import enrich_devices_with_mac
except ImportError:
    try:
        from arp_module import enrich_devices_with_mac
    except ImportError:
        enrich_devices_with_mac = None


class SSDPDiscovery:

    def __init__(self, search_targets: Optional[List[str]] = None):
        self.search_targets = search_targets or ["ssdp:all"]
        self.client = None
        self.devices = {}

    def start_discovery(self, duration: int = 10, mx: int = 2) -> Dict:
        try:
            self.client = SSDPClient()
            self.devices = {}

            print(f"Scanning for SSDP devices for {duration} seconds...")

            for search_target in self.search_targets:
                print(f"  Searching for: {search_target}")
                responses = self.client.m_search(st=search_target, mx=duration)
                for response in responses:
                    device_data = self._parse_device_info(response)
                    device_id = device_data.get(
                        "usn", device_data.get("location", "unknown")
                    )
                    if device_id not in self.devices:
                        self.devices[device_id] = device_data

                        print(f"\n[DEVICE DISCOVERED]")
                        print(f"Name: {device_data.get('name', 'Unknown')}")
                        print(f"Type: {device_data.get('type', 'Unknown')}")
                        print(f"Location: {device_data.get('location', 'Unknown')}")
                        print(f"IP Address: {device_data.get('ip_address', 'Unknown')}")
                        print("-" * 50)

            print(f"\nFound {len(self.devices)} SSDP device(s)")
            return self.devices

        except Exception as e:
            print(f"Error during SSDP discovery: {e}")
            return {}

    def _parse_device_info(self, response: Dict) -> Dict:
        device_data = {
            "name": None,
            "type": None,
            "ip_address": None,
            "mac_address": None,
            "port": None,
            "server": None,
            "location": None,
            "usn": None,
            "properties": {},
            "discovery_method": "ssdp",
        }

        if "usn" in response:
            device_data["usn"] = response["usn"]
            device_data["name"] = self._extract_name_from_usn(response["usn"])

        if "location" in response:
            device_data["location"] = response["location"]
            ip_port = self._extract_ip_port_from_url(response["location"])
            if ip_port:
                device_data["ip_address"] = ip_port["ip"]
                device_data["port"] = ip_port["port"]

        if "st" in response:
            device_data["type"] = response["st"]
        if "server" in response:
            device_data["server"] = response["server"]

        for key, value in response.items():
            if key.lower() not in ["usn", "location", "st", "server"]:
                device_data["properties"][key] = value

        if device_data["ip_address"]:
            device_data["mac_address"] = self._get_mac_address(
                device_data["ip_address"]
            )

        return device_data

    def _extract_name_from_usn(self, usn: str) -> str:
        if "::" in usn:
            parts = usn.split("::")
            if len(parts) >= 2:
                return parts[-1]
        return usn

    def _extract_ip_port_from_url(self, url: str) -> Optional[Dict]:
        try:
            match = re.match(r"https?://([^:]+):?(\d+)?", url)
            if match:
                ip = match.group(1)
                port = (
                    int(match.group(2))
                    if match.group(2)
                    else (443 if url.startswith("https") else 80)
                )
                return {"ip": ip, "port": port}
        except Exception as e:
            print(f"Error parsing URL: {e}")
        return None

    def _get_mac_address(self, ip_address: str) -> Optional[str]:
        if not ip_address:
            return None

        if enrich_devices_with_mac is not None:
            try:
                mac_mapping = enrich_devices_with_mac([ip_address], timeout=1)
                return mac_mapping.get(ip_address)
            except Exception:
                return None

        return None

    def get_discovered_devices(self) -> Dict:
        return self.devices.copy()


def discover_ssdp_devices(
    duration: int = 10, search_targets: Optional[List[str]] = None, mx: int = 2
) -> Dict:

    discovery = SSDPDiscovery(search_targets)
    return discovery.start_discovery(duration, mx)
