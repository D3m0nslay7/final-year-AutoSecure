"""
Network Scanner Library Module

This is a LIBRARY MODULE - it contains only class definitions and is designed
to be imported by other Python modules. It contains NO executable code outside
of class/function definitions.

Usage:
    from Engines.Discovery.modules.core import NetworkScanner

    scanner = NetworkScanner('192.168.1.0/24')
    devices = scanner.scan()

    for device in devices:
        print(f"Found: {device['ip']} ({device['mac']})")
"""

from scapy.all import ARP, Ether, srp
from datetime import datetime
from typing import List, Dict, Optional
import logging


class NetworkScanner:
    """
    NetworkScanner class for ARP-based network device discovery.

    This is a pure library class that performs ARP scans on a given subnet
    to discover active network devices. It uses scapy to send ARP broadcast
    requests and collects responses containing IP and MAC address information.

    Attributes:
        network_subnet (str): The network subnet to scan in CIDR notation
                             (e.g., "192.168.1.0/24")
        timeout (int): Timeout in seconds for ARP responses (default: 3)

    Example:
        >>> from Engines.Discovery.modules.core import NetworkScanner
        >>>
        >>> scanner = NetworkScanner('192.168.1.0/24', timeout=5)
        >>> devices = scanner.scan()
        >>>
        >>> for device in devices:
        ...     print(f"IP: {device['ip']}, MAC: {device['mac']}")
    """

    def __init__(self, network_subnet: str, timeout: int = 3):
        """
        Initialize the NetworkScanner with a subnet and timeout.

        Args:
            network_subnet: Network subnet in CIDR notation (e.g., "192.168.1.0/24")
            timeout: Timeout in seconds for ARP responses (default: 3)

        Raises:
            ValueError: If network_subnet is empty or invalid format
        """
        if not network_subnet:
            raise ValueError("network_subnet cannot be empty")

        self.network_subnet = network_subnet
        self.timeout = timeout
        self._logger = logging.getLogger(__name__)

    def scan(self) -> List[Dict[str, str]]:
        """
        Perform ARP scan on the configured subnet.

        Sends ARP broadcast requests to all hosts in the subnet and collects
        responses containing IP and MAC addresses. Each discovered device is
        timestamped with the discovery time.

        Returns:
            List of dictionaries containing device information:
            [
                {
                    'ip': '192.168.1.100',
                    'mac': 'aa:bb:cc:dd:ee:ff',
                    'discovered_at': '2025-10-22T12:30:45.123456'
                },
                ...
            ]

            Returns empty list if scan fails or no devices found.

        Raises:
            PermissionError: If the scan requires elevated privileges

        Example:
            >>> scanner = NetworkScanner('192.168.1.0/24')
            >>> devices = scanner.scan()
            >>> len(devices)
            5
        """
        try:
            # Send ARP request and get responses
            responses = self._send_arp_request()

            # Parse responses into structured data
            devices = self._parse_responses(responses)

            return devices

        except PermissionError:
            self._logger.error("ARP scanning requires administrator/root privileges")
            raise
        except Exception as e:
            self._logger.error(f"Error during ARP scan: {e}")
            return []

    def _send_arp_request(self) -> List:
        """
        Send ARP broadcast request and collect responses.

        Creates an ARP request packet for the entire subnet, wraps it in an
        Ethernet frame with broadcast destination, and sends it out. Waits
        for responses up to the configured timeout.

        Returns:
            List of (sent, received) packet pairs from scapy's srp() function

        Raises:
            PermissionError: If insufficient privileges for raw socket access
            Exception: For other network or scapy-related errors
        """
        try:
            # Create ARP request packet targeting the subnet
            arp_request = ARP(pdst=self.network_subnet)

            # Create Ethernet frame with broadcast MAC address
            broadcast_frame = Ether(dst="ff:ff:ff:ff:ff:ff")

            # Combine Ethernet frame and ARP request
            packet = broadcast_frame / arp_request

            # Send packet and receive responses
            # srp() returns tuple of (answered, unanswered) packets
            # verbose=0 suppresses scapy output
            answered_packets, _ = srp(packet, timeout=self.timeout, verbose=0)

            return answered_packets

        except PermissionError:
            raise
        except Exception as e:
            self._logger.error(f"Failed to send ARP request: {e}")
            raise

    def _parse_responses(self, responses: List) -> List[Dict[str, str]]:
        """
        Parse ARP responses into structured device data.

        Extracts IP and MAC addresses from each ARP response packet and
        creates a dictionary entry with timestamp information.

        Args:
            responses: List of (sent, received) packet pairs from srp()

        Returns:
            List of device dictionaries with 'ip', 'mac', and 'discovered_at' keys

        Example:
            Internal use only - called by scan() method
        """
        devices = []
        current_time = datetime.now().isoformat()

        try:
            for sent_packet, received_packet in responses:
                # Extract IP address from the ARP response (psrc = Protocol Source)
                ip_address = received_packet.psrc

                # Extract MAC address from the ARP response (hwsrc = Hardware Source)
                mac_address = received_packet.hwsrc

                # Create device entry
                device = {
                    'ip': ip_address,
                    'mac': mac_address,
                    'discovered_at': current_time
                }

                devices.append(device)

        except Exception as e:
            self._logger.error(f"Error parsing ARP responses: {e}")

        return devices
