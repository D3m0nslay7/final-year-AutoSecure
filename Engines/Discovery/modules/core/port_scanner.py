"""
Port Scanner Library Module
"""

import socket
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple


class PortScanner:

    def __init__(self, timeout: int = 1, max_workers: int = 10):

        if timeout <= 0:
            raise ValueError("timeout must be a positive integer")
        if max_workers <= 0:
            raise ValueError("max_workers must be a positive integer")

        self.timeout = timeout
        self.max_workers = max_workers
        self._logger = logging.getLogger(__name__)

    def scan_host(self, ip: str, ports: List[int]) -> Dict:

        start_time = time.time()
        open_ports = []
        closed_ports = []

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_port = {
                    executor.submit(self._check_port, ip, port): port for port in ports
                }
                for future in as_completed(future_to_port):
                    port = future_to_port[future]
                    try:
                        is_open = future.result()
                        if is_open:
                            open_ports.append(port)
                        else:
                            closed_ports.append(port)
                    except Exception as e:
                        self._logger.error(f"Error checking port {port}: {e}")
                        closed_ports.append(port)

            open_ports.sort()
            closed_ports.sort()

        except Exception as e:
            self._logger.error(f"Error during port scan of {ip}: {e}")
        scan_duration = round(time.time() - start_time, 3)

        return {
            "ip": ip,
            "open_ports": open_ports,
            "closed_ports": closed_ports,
            "scan_duration": scan_duration,
        }

    def scan_multiple_hosts(self, hosts: List[str], ports: List[int]) -> List[Dict]:

        results = []

        try:
            for host in hosts:
                result = self.scan_host(host, ports)
                results.append(result)

        except Exception as e:
            self._logger.error(f"Error during multiple host scan: {e}")

        return results

    def _check_port(self, ip: str, port: int) -> bool:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, port))

            return result == 0

        except socket.timeout:
            return False
        except socket.error:
            return False
        except Exception as e:
            self._logger.error(f"Unexpected error checking {ip}:{port}: {e}")
            return False
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
