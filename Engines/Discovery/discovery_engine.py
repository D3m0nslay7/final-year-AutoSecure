"""
Discovery Engine - Main orchestrator for device discovery
Coordinates multiple discovery methods (mDNS, network scanning, etc.)
"""

from typing import Dict, List, Optional

# Handle both standalone and module imports
if __name__ == "__main__":
    from modules.protocols.mdns_module import discover_mdns_devices
else:
    from .modules.protocols.mdns_module import discover_mdns_devices


class DiscoveryEngine:
    """
    Main discovery engine that orchestrates all device discovery methods
    Maintains a centralized registry of discovered devices
    """

    def __init__(self):
        self.discovered_devices: Dict[str, Dict] = {}
        self.discovery_methods: List[str] = []

    def discover_all(
        self, duration: int = 10, methods: Optional[List[str]] = None
    ) -> Dict:
        """
        Run all discovery methods and return combined results

        Args:
            duration: How long to scan for devices (seconds)
            methods: Optional list of methods to use. Default: ['mdns', 'ssdp']
                    Available: 'mdns', 'ssdp'
                    Note: ARP is automatically used to enrich discovered devices with MAC addresses
                    Future: 'nmap' (TODO)

        Returns:
            Dictionary of all discovered devices
        """
        methods = methods or [
            "mdns",
            "ssdp",
        ]  # Default methods (ARP used for enrichment)

        print("=" * 60)
        print("Starting Device Discovery Engine")
        print("=" * 60)

        # Calculate method count for progress display
        method_count = len([m for m in methods if m in ["mdns", "ssdp", "arp"]])
        current_method = 0

        # Run mDNS discovery
        if "mdns" in methods:
            current_method += 1
            print(f"\n[{current_method}/{method_count}] Running mDNS Discovery...")
            mdns_devices = self._discover_mdns(duration)
            self._merge_devices(mdns_devices)

        if "ssdp" in methods:
            current_method += 1
            print(f"\n[{current_method}/{method_count}] Running SSDP Discovery...")
            ssdp_devices = self._discover_ssdp(duration)
            self._merge_devices(ssdp_devices)

        if "arp" in methods:
            current_method += 1
            print(f"\n[{current_method}/{method_count}] Running ARP Discovery...")
            arp_devices = self._discover_arp(duration)
            self._merge_devices(arp_devices)

        # ARP enrichment - Add MAC addresses to already discovered devices
        if self.discovered_devices:
            print(
                f"\n[Enrichment] Using ARP to get MAC addresses for discovered devices..."
            )
            self._enrich_with_arp()

        # if 'nmap' in methods:
        #     print("\n[3/N] Running Nmap Discovery...")
        #     nmap_devices = self._discover_nmap()
        #     self._merge_devices(nmap_devices)

        print("\n" + "=" * 60)
        print(f"Discovery Complete - Total Devices: {len(self.discovered_devices)}")
        print("=" * 60)

        return self.get_all_devices()

    def _discover_mdns(self, duration: int = 10) -> Dict:
        """Run mDNS/Zeroconf discovery"""
        try:
            devices = discover_mdns_devices(duration=duration)
            return devices
        except Exception as e:
            print(f"Error during mDNS discovery: {e}")
            return {}

    def _discover_ssdp(self, duration: int = 10) -> Dict:
        """Run SSDP/UPnP discovery"""
        try:
            # Handle both standalone and module imports
            if __name__ == "__main__":
                from modules.protocols.ssdp_module import discover_ssdp_devices
            else:
                from .modules.protocols.ssdp_module import discover_ssdp_devices

            devices = discover_ssdp_devices(duration=duration)
            return devices
        except Exception as e:
            print(f"Error during SSDP discovery: {e}")
            return {}

    def _discover_arp(self, duration: int = 10) -> Dict:
        """Run ARP discovery"""
        try:
            # Handle both standalone and module imports
            if __name__ == "__main__":
                from modules.protocols.arp_module import discover_arp_devices
            else:
                from .modules.protocols.arp_module import discover_arp_devices

            devices = discover_arp_devices(duration=duration)
            return devices
        except PermissionError:
            print(
                "Warning: ARP scanning requires administrator/root privileges. Skipping ARP discovery."
            )
            return {}
        except Exception as e:
            print(f"Error during ARP discovery: {e}")
            return {}

    def _enrich_with_arp(self) -> None:
        """
        Use ARP to enrich already discovered devices with MAC addresses
        Only scans IPs of devices already found by mDNS/SSDP
        """
        try:
            # Handle both standalone and module imports
            if __name__ == "__main__":
                from modules.protocols.arp_module import enrich_devices_with_mac
            else:
                from .modules.protocols.arp_module import enrich_devices_with_mac

            # Get all IP addresses from discovered devices that need MAC addresses
            target_ips = []
            for device_id, device_info in self.discovered_devices.items():
                ip = device_info.get("ip_address")
                mac = device_info.get("mac_address")
                # Only query if we have an IP and don't already have a MAC
                if ip and not mac and ip not in target_ips:
                    target_ips.append(ip)

            if not target_ips:
                print("  No IP addresses to enrich")
                return

            # Get MAC addresses from ARP module
            mac_mapping = enrich_devices_with_mac(target_ips, timeout=1)

            # Update devices with MAC addresses
            for device_id, device_info in self.discovered_devices.items():
                ip = device_info.get("ip_address")
                if ip in mac_mapping:
                    device_info["mac_address"] = mac_mapping[ip]

        except Exception as e:
            print(f"  Warning: ARP enrichment failed: {e}")

    def _merge_devices(self, new_devices: Dict) -> None:
        """
        Merge newly discovered devices into the main registry
        Handle duplicates by IP address
        """
        for device_id, device_info in new_devices.items():
            ip_address = device_info.get("ip_address")

            # Check if we already have this device by IP
            existing_device = self._find_device_by_ip(ip_address)

            if existing_device:
                # Update existing device with new information
                existing_id = existing_device["id"]
                self.discovered_devices[existing_id] = self._merge_device_info(
                    self.discovered_devices[existing_id], device_info
                )
            else:
                # Add new device
                self.discovered_devices[device_id] = device_info
                self.discovered_devices[device_id]["id"] = device_id

    def _find_device_by_ip(self, ip_address: str) -> Optional[Dict]:
        """Find a device by its IP address"""
        if not ip_address:
            return None

        for device_id, device_info in self.discovered_devices.items():
            if device_info.get("ip_address") == ip_address:
                return {"id": device_id, **device_info}
        return None

    def _merge_device_info(self, existing: Dict, new: Dict) -> Dict:
        """
        Merge information from two device records
        Keeps the most complete information
        """
        merged = existing.copy()

        # Update fields that are missing or more complete in new record
        for key, value in new.items():
            if key not in merged or merged[key] is None:
                merged[key] = value
            elif key == "properties":
                # Merge properties dictionaries
                merged["properties"].update(value)
            elif key == "discovery_method":
                # Track all discovery methods
                if isinstance(merged[key], list):
                    if value not in merged[key]:
                        merged[key].append(value)
                else:
                    merged[key] = (
                        [merged[key], value] if merged[key] != value else merged[key]
                    )

        return merged

    def get_all_devices(self) -> Dict:
        """Get all discovered devices"""
        return self.discovered_devices.copy()

    def get_device_by_ip(self, ip_address: str) -> Optional[Dict]:
        """Get a specific device by IP address"""
        device = self._find_device_by_ip(ip_address)
        return device if device else None

    def get_device_by_mac(self, mac_address: str) -> Optional[Dict]:
        """Get a specific device by MAC address"""
        for device_id, device_info in self.discovered_devices.items():
            if device_info.get("mac_address") == mac_address:
                return {"id": device_id, **device_info}
        return None

    def get_devices_by_type(self, device_type: str) -> List[Dict]:
        """Get all devices of a specific type (e.g., '_hap._tcp.local.')"""
        matching_devices = []
        for device_id, device_info in self.discovered_devices.items():
            if device_info.get("type") == device_type:
                matching_devices.append({"id": device_id, **device_info})
        return matching_devices

    def print_summary(self) -> None:
        """Print a summary of all discovered devices"""
        print("\n" + "=" * 60)
        print(f"DISCOVERED DEVICES SUMMARY ({len(self.discovered_devices)} total)")
        print("=" * 60)

        if not self.discovered_devices:
            print("No devices discovered.")
            return

        for device_id, device in self.discovered_devices.items():
            print(f"\nDevice: {device.get('name', device_id)}")
            print(f"  IP Address:  {device.get('ip_address', 'Unknown')}")
            print(f"  MAC Address: {device.get('mac_address', 'Unknown')}")
            print(f"  Type:        {device.get('type', 'Unknown')}")
            print(f"  Port:        {device.get('port', 'Unknown')}")
            print(f"  Method:      {device.get('discovery_method', 'Unknown')}")

            if device.get("properties"):
                print(f"  Properties:  {len(device['properties'])} item(s)")

        print("\n" + "=" * 60)

    def export_devices(self, format: str = "dict") -> any:
        """
        Export discovered devices in various formats

        Args:
            format: Export format ('dict', 'json', 'csv')

        Returns:
            Devices in requested format
        """
        if format == "dict":
            return self.get_all_devices()
        elif format == "json":
            import json

            return json.dumps(self.get_all_devices(), indent=2)
        elif format == "csv":
            # TODO: Implement CSV export
            raise NotImplementedError("CSV export not yet implemented")
        else:
            raise ValueError(f"Unsupported format: {format}")


if __name__ == "__main__":
    # Allow standalone execution for quick testing
    print("Running Discovery Engine in standalone mode...")
    engine = DiscoveryEngine()
    devices = engine.discover_all(duration=10)
    engine.print_summary()
