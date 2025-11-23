"""
ARP Discovery Module
"""

# Prevent standalone execution
if __name__ == "__main__":
    raise RuntimeError("This module cannot be run standalone. ")

from scapy.all import ARP, Ether, srp
import ipaddress
from typing import Dict, List, Optional
import socket
import struct


class ARPDiscovery:
    """Main class for ARP device discovery"""

    def __init__(self, target_subnet: Optional[str] = None):
        self.target_subnet = target_subnet or self._detect_local_subnet()
        self.devices = {}

    def start_discovery(self, duration: int = 10, timeout: int = 2) -> Dict:
        try:
            self.devices = {}

            if not self.target_subnet:
                print("Could not determine target subnet. Please specify manually.")
                return {}

            print(f"Scanning subnet {self.target_subnet} via ARP...")
            arp = ARP(pdst=self.target_subnet)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether / arp

            result = srp(packet, timeout=timeout, verbose=0)[0]
            for sent, received in result:
                device_data = self._parse_device_info(received)
                device_id = device_data.get(
                    "mac_address", device_data.get("ip_address", "unknown")
                )
                if device_id not in self.devices:
                    self.devices[device_id] = device_data

                    print(f"\n[DEVICE DISCOVERED]")
                    print(f"IP Address: {device_data.get('ip_address', 'Unknown')}")
                    print(f"MAC Address: {device_data.get('mac_address', 'Unknown')}")
                    print(f"Vendor: {device_data.get('vendor', 'Unknown')}")
                    print("-" * 50)
            print(f"\nFound {len(self.devices)} device(s) via ARP")
            return self.devices

        except PermissionError:
            print("Error: ARP scanning requires administrator/root privileges")
            return {}
        except Exception as e:
            print(f"Error during ARP discovery: {e}")
            return {}

    def _parse_device_info(self, response) -> Dict:
        """Parse ARP response into structured device data"""
        device_data = {
            "name": None,
            "type": "arp",
            "ip_address": None,
            "mac_address": None,
            "port": None,
            "server": None,
            "vendor": None,
            "properties": {},
            "discovery_method": "arp",
        }
        if hasattr(response, "psrc"):
            device_data["ip_address"] = response.psrc
            device_data["name"] = self._resolve_hostname(response.psrc)

        if hasattr(response, "hwsrc"):
            device_data["mac_address"] = response.hwsrc
            device_data["vendor"] = self._get_vendor_from_mac(response.hwsrc)

        return device_data

    def _resolve_hostname(self, ip_address: str) -> Optional[str]:
        try:
            hostname = socket.gethostbyaddr(ip_address)[0]
            return hostname
        except (socket.herror, socket.gaierror):
            return None

    def _get_vendor_from_mac(self, mac_address: str) -> Optional[str]:
        _ = mac_address  # Unused for now
        return None

    def _detect_local_subnet(self) -> Optional[str]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            ip_obj = ipaddress.IPv4Address(local_ip)
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)

            return str(network)

        except Exception as e:
            print(f"Error detecting local subnet: {e}")
            return None

    def get_discovered_devices(self) -> Dict:
        """Return all discovered devices"""
        return self.devices.copy()


def discover_arp_devices(
    duration: int = 10, target_subnet: Optional[str] = None, timeout: int = 2
) -> Dict:
    discovery = ARPDiscovery(target_subnet)
    return discovery.start_discovery(duration, timeout)


def enrich_devices_with_mac(
    ip_addresses: List[str], timeout: int = 1
) -> Dict[str, str]:
    mac_mapping = {}

    if not ip_addresses:
        return mac_mapping

    try:
        from scapy.all import ARP, Ether, srp

        print(f"  Querying ARP for {len(ip_addresses)} device(s)...")

        for ip in ip_addresses:
            try:
                arp_request = ARP(pdst=ip)
                ether = Ether(dst="ff:ff:ff:ff:ff:ff")
                packet = ether / arp_request
                result = srp(packet, timeout=timeout, verbose=0)[0]

                if result:
                    for sent, received in result:
                        mac_address = received.hwsrc
                        mac_mapping[ip] = mac_address
                        print(f"  ✓ {ip} -> {mac_address}")
                        break

            except Exception as e:
                pass

        print(f"  Enriched {len(mac_mapping)} device(s) with MAC addresses")

    except PermissionError:
        print(
            "  Warning: ARP requires administrator/root privileges. Skipping enrichment."
        )
    except ImportError:
        print("  Warning: Scapy not installed. Install with: pip install scapy")
    except Exception as e:
        print(f"  Warning: ARP enrichment failed: {e}")

    return mac_mapping
