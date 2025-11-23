"""
MQTT Broker Detector Library Module

This is a LIBRARY MODULE - it contains only class definitions and is designed
to be imported by other Python modules. It contains NO executable code outside
of class/function definitions.

Usage:
    from Engines.Discovery.modules.core import NetworkScanner, PortScanner
    from Engines.Discovery.modules.protocols import MQTTBrokerDetector

    # Discover devices on network
    net_scanner = NetworkScanner('192.168.1.0/24')
    devices = net_scanner.scan()

    # Find MQTT brokers among discovered devices
    port_scanner = PortScanner()
    mqtt_detector = MQTTBrokerDetector(port_scanner)
    brokers = mqtt_detector.find_brokers(devices)

    # Use results
    for broker in brokers:
        print(f"Found {broker['vendor']} broker at {broker['ip']}:{broker['port']}")
"""

import socket
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import requests


class MQTTBrokerDetector:
    """
    MQTTBrokerDetector class for identifying MQTT brokers on a network.

    This is a pure library class that performs a 3-stage discovery process:
    1. Finds devices with open MQTT ports using PortScanner
    2. Verifies MQTT protocol by attempting handshake
    3. Identifies broker vendor (HiveMQ, Mosquitto, EMQX, etc.)

    Attributes:
        port_scanner: Instance of PortScanner to use for port checking
        mqtt_ports (list): List of ports to check for MQTT (default: [1883, 8883, 8884, 8080, 8000])
        timeout (int): Connection timeout in seconds (default: 2)

    Example:
        >>> from Engines.Discovery.modules.core import NetworkScanner, PortScanner
        >>> from Engines.Discovery.modules.protocols import MQTTBrokerDetector
        >>>
        >>> net_scanner = NetworkScanner('192.168.1.0/24')
        >>> devices = net_scanner.scan()
        >>>
        >>> port_scanner = PortScanner(timeout=2)
        >>> mqtt_detector = MQTTBrokerDetector(port_scanner)
        >>> brokers = mqtt_detector.find_brokers(devices)
        >>>
        >>> for broker in brokers:
        ...     print(f"{broker['vendor']} at {broker['ip']}:{broker['port']}")
    """

    # Common MQTT ports
    DEFAULT_MQTT_PORTS = [1883, 8883, 8884, 8080, 8000]

    # Vendor-specific web interface ports
    VENDOR_WEB_PORTS = {
        'hivemq': [8000, 8080, 8888],
        'emqx': [18083, 8083],
        'vernemq': [8888],
        'rabbitmq': [15672],
        'activemq': [8161]
    }

    # Vendor-specific cluster ports
    VENDOR_CLUSTER_PORTS = {
        'hivemq': [7800, 7801],
        'emqx': [4370, 8081],
        'vernemq': [44053]
    }

    def __init__(self, port_scanner, mqtt_ports: Optional[List[int]] = None, timeout: int = 2):
        """
        Initialize the MQTTBrokerDetector.

        Args:
            port_scanner: Instance of PortScanner to use for port checking
            mqtt_ports: List of ports to check (default: [1883, 8883, 8884, 8080, 8000])
            timeout: Connection timeout in seconds (default: 2)

        Raises:
            ValueError: If timeout is not positive or port_scanner is None
        """
        if port_scanner is None:
            raise ValueError("port_scanner cannot be None")
        if timeout <= 0:
            raise ValueError("timeout must be a positive integer")

        self.port_scanner = port_scanner
        self.mqtt_ports = mqtt_ports or self.DEFAULT_MQTT_PORTS
        self.timeout = timeout
        self._logger = logging.getLogger(__name__)

    def find_brokers(self, devices: List[Dict]) -> List[Dict]:
        """
        Main method: Find all MQTT brokers from discovered devices.

        Performs a 3-stage discovery process:
        1. Finds devices with open MQTT ports
        2. Verifies MQTT protocol by attempting connection
        3. Identifies broker vendor and features

        Args:
            devices: List of device dicts from NetworkScanner with 'ip' and 'mac' keys

        Returns:
            List of broker dictionaries with complete details:
            [
                {
                    'ip': '192.168.1.100',
                    'mac': 'aa:bb:cc:dd:ee:ff',
                    'port': 1883,
                    'is_mqtt': True,
                    'mqtt_version': '3.1.1',
                    'vendor': 'HiveMQ',
                    'features': ['WebSocket', 'TLS'],
                    'additional_ports': [8883, 8080],
                    'discovered_at': '2025-01-15T10:30:00.123456'
                },
                ...
            ]

        Example:
            >>> devices = [{'ip': '192.168.1.100', 'mac': 'aa:bb:cc:dd:ee:ff'}]
            >>> brokers = detector.find_brokers(devices)
            >>> len(brokers)
            1
        """
        if not devices:
            return []

        try:
            # Stage 1: Find devices with open MQTT ports
            candidates = self._find_candidates(devices)

            if not candidates:
                return []

            # Stage 2 & 3: Verify MQTT protocol and identify vendors
            brokers = []
            for candidate in candidates:
                ip = candidate['ip']
                mac = candidate.get('mac')
                open_ports = candidate['open_ports']

                # Try each open port to verify MQTT
                for port in open_ports:
                    self._logger.debug(f"Verifying MQTT protocol on {ip}:{port}")
                    is_mqtt, mqtt_version = self._verify_mqtt_protocol(ip, port)

                    if is_mqtt:
                        self._logger.debug(f"✓ Confirmed MQTT on {ip}:{port} (version {mqtt_version})")
                    else:
                        self._logger.debug(f"✗ Not MQTT on {ip}:{port}")

                    if is_mqtt:
                        # Identify vendor and features
                        vendor_info = self._identify_vendor(ip, port)

                        # Get other MQTT ports on this host (excluding current port)
                        other_mqtt_ports = [p for p in open_ports if p != port]

                        broker = {
                            'ip': ip,
                            'mac': mac,
                            'port': port,
                            'is_mqtt': True,
                            'mqtt_version': mqtt_version,
                            'vendor': vendor_info.get('vendor', 'Unknown MQTT Broker'),
                            'features': vendor_info.get('features', []),
                            'additional_ports': other_mqtt_ports,
                            'discovered_at': datetime.now().isoformat()
                        }

                        brokers.append(broker)
                        self._logger.info(f"Found MQTT broker at {ip}:{port} - {broker['vendor']}")

                        # Continue checking other ports (allows multiple brokers per IP)

            return brokers

        except Exception as e:
            self._logger.error(f"Error during broker discovery: {e}")
            return []

    def _find_candidates(self, devices: List[Dict]) -> List[Dict]:
        """
        Stage 1: Find devices with open MQTT ports.

        Uses the PortScanner to check each device for open MQTT-related ports.

        Args:
            devices: List of device dicts with 'ip' and 'mac' keys

        Returns:
            List of devices with open MQTT ports:
            [
                {
                    'ip': '192.168.1.100',
                    'mac': 'aa:bb:cc:dd:ee:ff',
                    'open_ports': [1883, 8883]
                },
                ...
            ]
        """
        candidates = []

        try:
            # Extract IP addresses from devices
            ip_addresses = [device.get('ip') for device in devices if device.get('ip')]

            if not ip_addresses:
                return []

            # DEBUG: Show which ports we're checking
            self._logger.debug(f"Checking {len(ip_addresses)} devices for MQTT ports: {self.mqtt_ports}")

            # Scan all devices for MQTT ports
            scan_results = self.port_scanner.scan_multiple_hosts(ip_addresses, self.mqtt_ports)

            # Filter devices with open ports and add MAC addresses
            for result in scan_results:
                if result.get('open_ports'):
                    ip = result['ip']

                    # DEBUG: Show which ports were found open
                    self._logger.debug(f"Found open MQTT ports on {ip}: {result['open_ports']}")

                    # Find the corresponding device to get MAC address
                    mac = None
                    for device in devices:
                        if device.get('ip') == ip:
                            mac = device.get('mac')
                            break

                    candidates.append({
                        'ip': ip,
                        'mac': mac,
                        'open_ports': result['open_ports']
                    })

            self._logger.debug(f"Total candidates with open MQTT ports: {len(candidates)}")
            return candidates

        except Exception as e:
            self._logger.error(f"Error finding MQTT port candidates: {e}")
            return []

    def _verify_mqtt_protocol(self, ip: str, port: int) -> Tuple[bool, Optional[str]]:
        """
        Stage 2: Verify device is running MQTT protocol.

        Attempts to establish a raw socket connection and send an MQTT CONNECT
        packet to verify the service is actually MQTT. Tests both MQTT 3.1.1
        and MQTT 5.0 protocols.

        Args:
            ip: IP address to check
            port: Port to check

        Returns:
            Tuple of (is_mqtt: bool, mqtt_version: str or None)
            Examples: (True, '3.1.1'), (True, '5.0'), (False, None)

        Note:
            This method uses raw socket connections to send MQTT CONNECT packets.
            A proper CONNACK response confirms MQTT protocol.
        """
        # Try MQTT 3.1.1 first (more common)
        if self._try_mqtt_connect(ip, port, version='3.1.1'):
            return True, '3.1.1'

        # Try MQTT 5.0
        if self._try_mqtt_connect(ip, port, version='5.0'):
            return True, '5.0'

        return False, None

    def _try_mqtt_connect(self, ip: str, port: int, version: str = '3.1.1') -> bool:
        """
        Attempt to connect to an MQTT broker with a specific protocol version.

        Creates a minimal MQTT CONNECT packet and sends it to the broker.
        A valid CONNACK response confirms the MQTT protocol.

        Args:
            ip: IP address of the broker
            port: Port number
            version: MQTT version ('3.1.1' or '5.0')

        Returns:
            True if MQTT connection successful, False otherwise
        """
        sock = None
        try:
            # Create TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            # Connect to broker
            sock.connect((ip, port))

            # Build minimal MQTT CONNECT packet
            connect_packet = self._build_mqtt_connect_packet(version)

            # Send CONNECT packet
            sock.sendall(connect_packet)

            # Wait for CONNACK response
            response = sock.recv(4)

            # Valid CONNACK packet starts with 0x20 (CONNACK packet type)
            if response and len(response) >= 2 and response[0] == 0x20:
                return True

            return False

        except socket.timeout:
            return False
        except socket.error:
            return False
        except Exception as e:
            self._logger.debug(f"MQTT connect attempt failed for {ip}:{port} (v{version}): {e}")
            return False
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _build_mqtt_connect_packet(self, version: str = '3.1.1') -> bytes:
        """
        Build a minimal MQTT CONNECT packet.

        Args:
            version: MQTT version ('3.1.1' or '5.0')

        Returns:
            Bytes representing a minimal MQTT CONNECT packet
        """
        if version == '5.0':
            # MQTT 5.0 CONNECT packet
            # Fixed header: 0x10 (CONNECT), remaining length
            # Variable header: protocol name, protocol level (5), connect flags, keep alive
            # Payload: client ID
            return bytes([
                0x10,  # CONNECT packet type
                0x10,  # Remaining length
                0x00, 0x04,  # Protocol name length
                0x4d, 0x51, 0x54, 0x54,  # "MQTT"
                0x05,  # Protocol level (5 for MQTT 5.0)
                0x02,  # Connect flags (Clean Start)
                0x00, 0x3c,  # Keep alive (60 seconds)
                0x00,  # Properties length
                0x00, 0x04,  # Client ID length
                0x74, 0x65, 0x73, 0x74  # "test"
            ])
        else:
            # MQTT 3.1.1 CONNECT packet
            return bytes([
                0x10,  # CONNECT packet type
                0x10,  # Remaining length
                0x00, 0x04,  # Protocol name length
                0x4d, 0x51, 0x54, 0x54,  # "MQTT"
                0x04,  # Protocol level (4 for MQTT 3.1.1)
                0x02,  # Connect flags (Clean Session)
                0x00, 0x3c,  # Keep alive (60 seconds)
                0x00, 0x04,  # Client ID length
                0x74, 0x65, 0x73, 0x74  # "test"
            ])

    def _identify_vendor(self, ip: str, port: int) -> Dict:
        """
        Stage 3: Try to identify broker vendor and features.

        Attempts to identify the MQTT broker vendor using multiple methods:
        - Port-based identification (standard ports suggest specific vendors)
        - Check for vendor-specific web interfaces
        - Check for vendor-specific cluster ports
        - Identify available features (TLS, WebSocket, etc.)

        Args:
            ip: Broker IP address
            port: MQTT port

        Returns:
            Dictionary with vendor information:
            {
                'vendor': 'HiveMQ' or 'Unknown MQTT Broker',
                'features': ['TLS', 'WebSocket', ...]
            }
        """
        vendor_info = {
            'vendor': 'Unknown MQTT Broker',
            'features': []
        }

        try:
            # Port-based vendor hints (common conventions)
            # This helps when multiple brokers run on same host
            port_vendor_hints = {
                1883: 'Mosquitto',  # Standard port - default to Mosquitto
                8883: 'HiveMQ',     # HiveMQ commonly uses this for TLS
                8884: 'EMQX',       # EMQX commonly uses this for WebSocket
            }

            # Start with port-based hint
            if port in port_vendor_hints:
                suspected_vendor = port_vendor_hints[port]

                # Verify the hint by checking vendor-specific ports
                if suspected_vendor == 'Mosquitto':
                    # For standard port 1883, assume Mosquitto unless we find evidence of other vendors
                    # Don't check general web interface as it might match other brokers on same host
                    vendor_info['vendor'] = 'Mosquitto'
                    self._logger.debug(f"Port 1883 identified as Mosquitto (standard MQTT port)")

                elif suspected_vendor == 'HiveMQ':
                    # Check HiveMQ web interface on port 8000
                    if self._check_specific_web_port(ip, 8000, ['hivemq']):
                        vendor_info['vendor'] = 'HiveMQ'
                        self._logger.debug(f"Confirmed HiveMQ via web interface on port 8000")

                elif suspected_vendor == 'EMQX':
                    # Check EMQX dashboard on port 18083
                    if self._check_specific_web_port(ip, 18083, ['emqx']):
                        vendor_info['vendor'] = 'EMQX'
                        self._logger.debug(f"Confirmed EMQX via dashboard on port 18083")

            # If no port hint, try general web interface check (but not for port 1883)
            if vendor_info['vendor'] == 'Unknown MQTT Broker' and port != 1883:
                web_vendor = self._check_web_interface(ip)
                if web_vendor:
                    vendor_info['vendor'] = web_vendor

            # If still not found, try cluster ports
            if vendor_info['vendor'] == 'Unknown MQTT Broker':
                cluster_vendor = self._check_cluster_ports(ip)
                if cluster_vendor:
                    vendor_info['vendor'] = cluster_vendor

            # Identify features based on port
            features = []
            if port == 8883:
                features.append('TLS')
            if port in [8080, 8000, 8884]:
                features.append('WebSocket')

            vendor_info['features'] = features

            return vendor_info

        except Exception as e:
            self._logger.debug(f"Error identifying vendor for {ip}:{port}: {e}")
            return vendor_info

    def _check_specific_web_port(self, ip: str, port: int, keywords: List[str]) -> bool:
        """
        Check if a specific web port contains vendor keywords.

        Args:
            ip: IP address to check
            port: Port to check
            keywords: List of keywords to search for (lowercase)

        Returns:
            True if any keyword found, False otherwise
        """
        try:
            url = f"http://{ip}:{port}"
            response = requests.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                verify=False
            )

            content = response.text.lower()

            # Check if any keyword is in content
            for keyword in keywords:
                if keyword in content:
                    return True

            return False

        except Exception:
            return False

    def _check_web_interface(self, ip: str) -> Optional[str]:
        """
        Check for vendor-specific web interfaces.

        Attempts HTTP requests to common vendor web interface ports
        and checks response content for vendor keywords.

        Args:
            ip: IP address to check

        Returns:
            Vendor name if identified, None otherwise
        """
        for vendor, ports in self.VENDOR_WEB_PORTS.items():
            for port in ports:
                try:
                    # Try HTTP request with short timeout
                    url = f"http://{ip}:{port}"
                    response = requests.get(
                        url,
                        timeout=self.timeout,
                        allow_redirects=True,
                        verify=False
                    )

                    # Check response content for vendor keywords
                    content = response.text.lower()

                    # Vendor-specific keywords
                    vendor_keywords = {
                        'hivemq': ['hivemq', 'hive mq'],
                        'emqx': ['emqx', 'emq x'],
                        'mosquitto': ['mosquitto'],
                        'vernemq': ['vernemq', 'verne mq'],
                        'rabbitmq': ['rabbitmq', 'rabbit mq'],
                        'activemq': ['activemq', 'active mq']
                    }

                    # Check if any vendor keyword is in content
                    for v, keywords in vendor_keywords.items():
                        if any(keyword in content for keyword in keywords):
                            # Return properly capitalized vendor name
                            return self._capitalize_vendor_name(v)

                except requests.exceptions.Timeout:
                    continue
                except requests.exceptions.ConnectionError:
                    continue
                except Exception:
                    continue

        return None

    def _check_cluster_ports(self, ip: str) -> Optional[str]:
        """
        Check for vendor-specific cluster ports.

        Some MQTT brokers use specific ports for clustering.
        Checking if these ports are open can help identify the vendor.

        Args:
            ip: IP address to check

        Returns:
            Vendor name if identified, None otherwise
        """
        for vendor, ports in self.VENDOR_CLUSTER_PORTS.items():
            try:
                # Use port scanner to check vendor-specific ports
                result = self.port_scanner.scan_host(ip, ports)

                if result.get('open_ports'):
                    return self._capitalize_vendor_name(vendor)

            except Exception:
                continue

        return None

    def _capitalize_vendor_name(self, vendor: str) -> str:
        """
        Properly capitalize vendor names.

        Args:
            vendor: Lowercase vendor name

        Returns:
            Properly capitalized vendor name
        """
        vendor_map = {
            'hivemq': 'HiveMQ',
            'emqx': 'EMQX',
            'mosquitto': 'Mosquitto',
            'vernemq': 'VerneMQ',
            'rabbitmq': 'RabbitMQ',
            'activemq': 'ActiveMQ'
        }

        return vendor_map.get(vendor.lower(), vendor.capitalize())
