"""
Network Scanner Library Module
"""

from scapy.all import ARP, Ether, srp
from datetime import datetime
from typing import List, Dict, Optional
import logging


class NetworkScanner:
    def __init__(self, network_subnet: str, timeout: int = 3):
        if not network_subnet:
            raise ValueError("network_subnet cannot be empty")

        self.network_subnet = network_subnet
        self.timeout = timeout
        self._logger = logging.getLogger(__name__)

    def scan(self) -> List[Dict[str, str]]:
        try:
            responses = self._send_arp_request()
            devices = self._parse_responses(responses)

            return devices

        except PermissionError:
            self._logger.error("ARP scanning requires administrator/root privileges")
            raise
        except Exception as e:
            self._logger.error(f"Error during ARP scan: {e}")
            return []

    def _send_arp_request(self) -> List:
        try:
            arp_request = ARP(pdst=self.network_subnet)
            broadcast_frame = Ether(dst="ff:ff:ff:ff:ff:ff")

            packet = broadcast_frame / arp_request

            answered_packets, _ = srp(packet, timeout=self.timeout, verbose=0)

            return answered_packets

        except PermissionError:
            raise
        except Exception as e:
            self._logger.error(f"Failed to send ARP request: {e}")
            raise

    def _parse_responses(self, responses: List) -> List[Dict[str, str]]:

        devices = []
        current_time = datetime.now().isoformat()

        try:
            for sent_packet, received_packet in responses:

                ip_address = received_packet.psrc
                mac_address = received_packet.hwsrc
                device = {
                    "ip": ip_address,
                    "mac": mac_address,
                    "discovered_at": current_time,
                }

                devices.append(device)

        except Exception as e:
            self._logger.error(f"Error parsing ARP responses: {e}")

        return devices
