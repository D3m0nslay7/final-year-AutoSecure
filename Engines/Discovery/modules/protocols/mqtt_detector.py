"""
MQTT Broker Detector Library Module
"""

import socket
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import requests


class MQTTBrokerDetector:
    DEFAULT_MQTT_PORTS = [1883, 8883, 8884, 8080, 8000]

    VENDOR_WEB_PORTS = {
        "hivemq": [8000, 8080, 8888],
        "emqx": [18083, 8083],
        "vernemq": [8888],
        "rabbitmq": [15672],
        "activemq": [8161],
    }

    VENDOR_CLUSTER_PORTS = {
        "hivemq": [7800, 7801],
        "emqx": [4370, 8081],
        "vernemq": [44053],
    }

    def __init__(
        self, port_scanner, mqtt_ports: Optional[List[int]] = None, timeout: int = 2
    ):
        if port_scanner is None:
            raise ValueError("port_scanner cannot be None")
        if timeout <= 0:
            raise ValueError("timeout must be a positive integer")

        self.port_scanner = port_scanner
        self.mqtt_ports = mqtt_ports or self.DEFAULT_MQTT_PORTS
        self.timeout = timeout
        self._logger = logging.getLogger(__name__)

    def find_brokers(self, devices: List[Dict]) -> List[Dict]:
        if not devices:
            return []

        try:
            candidates = self._find_candidates(devices)

            if not candidates:
                return []

            brokers = []
            for candidate in candidates:
                ip = candidate["ip"]
                mac = candidate.get("mac")
                open_ports = candidate["open_ports"]

                for port in open_ports:
                    self._logger.debug(f"Verifying MQTT protocol on {ip}:{port}")
                    is_mqtt, mqtt_version = self._verify_mqtt_protocol(ip, port)

                    if is_mqtt:
                        self._logger.debug(
                            f"✓ Confirmed MQTT on {ip}:{port} (version {mqtt_version})"
                        )
                    else:
                        self._logger.debug(f"✗ Not MQTT on {ip}:{port}")

                    if is_mqtt:
                        vendor_info = self._identify_vendor(ip, port)
                        other_mqtt_ports = [p for p in open_ports if p != port]

                        broker = {
                            "ip": ip,
                            "mac": mac,
                            "port": port,
                            "is_mqtt": True,
                            "mqtt_version": mqtt_version,
                            "vendor": vendor_info.get("vendor", "Unknown MQTT Broker"),
                            "features": vendor_info.get("features", []),
                            "additional_ports": other_mqtt_ports,
                            "discovered_at": datetime.now().isoformat(),
                        }

                        brokers.append(broker)
                        self._logger.info(
                            f"Found MQTT broker at {ip}:{port} - {broker['vendor']}"
                        )

            return brokers

        except Exception as e:
            self._logger.error(f"Error during broker discovery: {e}")
            return []

    def _find_candidates(self, devices: List[Dict]) -> List[Dict]:
        candidates = []

        try:
            ip_addresses = [device.get("ip") for device in devices if device.get("ip")]

            if not ip_addresses:
                return []

            scan_results = self.port_scanner.scan_multiple_hosts(
                ip_addresses, self.mqtt_ports
            )

            for result in scan_results:
                if result.get("open_ports"):
                    ip = result["ip"]

                    mac = None
                    for device in devices:
                        if device.get("ip") == ip:
                            mac = device.get("mac")
                            break

                    candidates.append(
                        {"ip": ip, "mac": mac, "open_ports": result["open_ports"]}
                    )

            self._logger.debug(
                f"Total candidates with open MQTT ports: {len(candidates)}"
            )
            return candidates

        except Exception as e:
            self._logger.error(f"Error finding MQTT port candidates: {e}")
            return []

    def _verify_mqtt_protocol(self, ip: str, port: int) -> Tuple[bool, Optional[str]]:
        if self._try_mqtt_connect(ip, port, version="3.1.1"):
            return True, "3.1.1"

        if self._try_mqtt_connect(ip, port, version="5.0"):
            return True, "5.0"

        return False, None

    def _try_mqtt_connect(self, ip: str, port: int, version: str = "3.1.1") -> bool:

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((ip, port))
            connect_packet = self._build_mqtt_connect_packet(version)
            sock.sendall(connect_packet)
            response = sock.recv(4)
            if response and len(response) >= 2 and response[0] == 0x20:
                return True

            return False

        except socket.timeout:
            return False
        except socket.error:
            return False
        except Exception as e:
            self._logger.debug(
                f"MQTT connect attempt failed for {ip}:{port} (v{version}): {e}"
            )
            return False
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _build_mqtt_connect_packet(self, version: str = "3.1.1") -> bytes:
        if version == "5.0":
            return bytes(
                [
                    0x10,  # CONNECT packet type
                    0x10,  # Remaining length
                    0x00,
                    0x04,  # Protocol name length
                    0x4D,
                    0x51,
                    0x54,
                    0x54,  # "MQTT"
                    0x05,  # Protocol level (5 for MQTT 5.0)
                    0x02,  # Connect flags (Clean Start)
                    0x00,
                    0x3C,  # Keep alive (60 seconds)
                    0x00,  # Properties length
                    0x00,
                    0x04,  # Client ID length
                    0x74,
                    0x65,
                    0x73,
                    0x74,  # "test"
                ]
            )
        else:
            return bytes(
                [
                    0x10,  # CONNECT packet type
                    0x10,  # Remaining length
                    0x00,
                    0x04,  # Protocol name length
                    0x4D,
                    0x51,
                    0x54,
                    0x54,  # "MQTT"
                    0x04,  # Protocol level (4 for MQTT 3.1.1)
                    0x02,  # Connect flags (Clean Session)
                    0x00,
                    0x3C,  # Keep alive (60 seconds)
                    0x00,
                    0x04,  # Client ID length
                    0x74,
                    0x65,
                    0x73,
                    0x74,  # "test"
                ]
            )

    def _identify_vendor(self, ip: str, port: int) -> Dict:
        vendor_info = {"vendor": "Unknown MQTT Broker", "features": []}

        try:
            port_vendor_hints = {
                1883: "Mosquitto",  # Standard port - default to Mosquitto
                8883: "HiveMQ",  # HiveMQ commonly uses this for TLS
                8884: "EMQX",  # EMQX commonly uses this for WebSocket
            }

            if port in port_vendor_hints:
                suspected_vendor = port_vendor_hints[port]
                if suspected_vendor == "Mosquitto":
                    vendor_info["vendor"] = "Mosquitto"
                    self._logger.debug(
                        f"Port 1883 identified as Mosquitto (standard MQTT port)"
                    )

                elif suspected_vendor == "HiveMQ":
                    if self._check_specific_web_port(ip, 8000, ["hivemq"]):
                        vendor_info["vendor"] = "HiveMQ"
                        self._logger.debug(
                            f"Confirmed HiveMQ via web interface on port 8000"
                        )

                elif suspected_vendor == "EMQX":
                    if self._check_specific_web_port(ip, 18083, ["emqx"]):
                        vendor_info["vendor"] = "EMQX"
                        self._logger.debug(
                            f"Confirmed EMQX via dashboard on port 18083"
                        )

            if vendor_info["vendor"] == "Unknown MQTT Broker" and port != 1883:
                web_vendor = self._check_web_interface(ip)
                if web_vendor:
                    vendor_info["vendor"] = web_vendor
            if vendor_info["vendor"] == "Unknown MQTT Broker":
                cluster_vendor = self._check_cluster_ports(ip)
                if cluster_vendor:
                    vendor_info["vendor"] = cluster_vendor

            features = []
            if port == 8883:
                features.append("TLS")
            if port in [8080, 8000, 8884]:
                features.append("WebSocket")

            vendor_info["features"] = features

            return vendor_info

        except Exception as e:
            self._logger.debug(f"Error identifying vendor for {ip}:{port}: {e}")
            return vendor_info

    def _check_specific_web_port(self, ip: str, port: int, keywords: List[str]) -> bool:
        try:
            url = f"http://{ip}:{port}"
            response = requests.get(
                url, timeout=self.timeout, allow_redirects=True, verify=False
            )

            content = response.text.lower()
            for keyword in keywords:
                if keyword in content:
                    return True

            return False

        except Exception:
            return False

    def _check_web_interface(self, ip: str) -> Optional[str]:
        for vendor, ports in self.VENDOR_WEB_PORTS.items():
            for port in ports:
                try:
                    url = f"http://{ip}:{port}"
                    response = requests.get(
                        url, timeout=self.timeout, allow_redirects=True, verify=False
                    )
                    content = response.text.lower()

                    vendor_keywords = {
                        "hivemq": ["hivemq", "hive mq"],
                        "emqx": ["emqx", "emq x"],
                        "mosquitto": ["mosquitto"],
                        "vernemq": ["vernemq", "verne mq"],
                        "rabbitmq": ["rabbitmq", "rabbit mq"],
                        "activemq": ["activemq", "active mq"],
                    }
                    for v, keywords in vendor_keywords.items():
                        if any(keyword in content for keyword in keywords):
                            return self._capitalize_vendor_name(v)

                except requests.exceptions.Timeout:
                    continue
                except requests.exceptions.ConnectionError:
                    continue
                except Exception:
                    continue

        return None

    def _check_cluster_ports(self, ip: str) -> Optional[str]:
        for vendor, ports in self.VENDOR_CLUSTER_PORTS.items():
            try:
                result = self.port_scanner.scan_host(ip, ports)

                if result.get("open_ports"):
                    return self._capitalize_vendor_name(vendor)

            except Exception:
                continue

        return None

    def _capitalize_vendor_name(self, vendor: str) -> str:
        vendor_map = {
            "hivemq": "HiveMQ",
            "emqx": "EMQX",
            "mosquitto": "Mosquitto",
            "vernemq": "VerneMQ",
            "rabbitmq": "RabbitMQ",
            "activemq": "ActiveMQ",
        }

        return vendor_map.get(vendor.lower(), vendor.capitalize())
