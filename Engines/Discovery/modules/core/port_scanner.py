"""
Port Scanner Library Module

This is a LIBRARY MODULE - it contains only class definitions and is designed
to be imported by other Python modules. It contains NO executable code outside
of class/function definitions.

Usage:
    from Engines.Discovery.modules.core import PortScanner

    scanner = PortScanner(timeout=1, max_workers=10)
    result = scanner.scan_host('192.168.1.100', [1883, 8883, 8884])

    print(f"Open ports: {result['open_ports']}")
    print(f"Scan took: {result['scan_duration']} seconds")
"""

import socket
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple


class PortScanner:
    """
    PortScanner class for TCP port availability checking.

    This is a pure library class that performs TCP connection attempts to
    determine if ports are open or closed. It uses concurrent threading to
    scan multiple ports in parallel for improved performance.

    Attributes:
        timeout (int): Connection timeout in seconds (default: 1)
        max_workers (int): Maximum number of concurrent threads (default: 10)

    Example:
        >>> from Engines.Discovery.modules.core import PortScanner
        >>>
        >>> scanner = PortScanner(timeout=2, max_workers=20)
        >>> result = scanner.scan_host('192.168.1.100', [80, 443, 22, 3389])
        >>>
        >>> print(f"Open ports: {result['open_ports']}")
        >>> print(f"Closed ports: {result['closed_ports']}")
        >>> print(f"Scan duration: {result['scan_duration']} seconds")
    """

    def __init__(self, timeout: int = 1, max_workers: int = 10):
        """
        Initialize the PortScanner with timeout and thread pool configuration.

        Args:
            timeout: Connection timeout in seconds (default: 1)
            max_workers: Maximum number of concurrent threads for parallel
                        scanning (default: 10)

        Raises:
            ValueError: If timeout or max_workers are not positive integers
        """
        if timeout <= 0:
            raise ValueError("timeout must be a positive integer")
        if max_workers <= 0:
            raise ValueError("max_workers must be a positive integer")

        self.timeout = timeout
        self.max_workers = max_workers
        self._logger = logging.getLogger(__name__)

    def scan_host(self, ip: str, ports: List[int]) -> Dict:
        """
        Scan a single host for a list of ports.

        Attempts TCP connections to each port in the list concurrently.
        Categorizes ports as open or closed based on connection success.

        Args:
            ip: IP address of the host to scan (e.g., '192.168.1.100')
            ports: List of port numbers to check (e.g., [80, 443, 22])

        Returns:
            Dictionary containing scan results:
            {
                'ip': '192.168.1.100',
                'open_ports': [80, 443],
                'closed_ports': [22],
                'scan_duration': 1.234
            }

        Example:
            >>> scanner = PortScanner()
            >>> result = scanner.scan_host('192.168.1.1', [80, 443, 8080])
            >>> if 80 in result['open_ports']:
            ...     print("HTTP port is open")
        """
        start_time = time.time()
        open_ports = []
        closed_ports = []

        try:
            # Use ThreadPoolExecutor for concurrent port checking
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all port check tasks
                future_to_port = {
                    executor.submit(self._check_port, ip, port): port
                    for port in ports
                }

                # Collect results as they complete
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

            # Sort ports for consistent output
            open_ports.sort()
            closed_ports.sort()

        except Exception as e:
            self._logger.error(f"Error during port scan of {ip}: {e}")

        # Calculate scan duration
        scan_duration = round(time.time() - start_time, 3)

        return {
            'ip': ip,
            'open_ports': open_ports,
            'closed_ports': closed_ports,
            'scan_duration': scan_duration
        }

    def scan_multiple_hosts(self, hosts: List[str], ports: List[int]) -> List[Dict]:
        """
        Scan multiple hosts for the same list of ports.

        Performs port scanning on multiple hosts sequentially. Each host is
        scanned with concurrent port checking as in scan_host().

        Args:
            hosts: List of IP addresses to scan (e.g., ['192.168.1.1', '192.168.1.2'])
            ports: List of port numbers to check on each host

        Returns:
            List of scan result dictionaries, one per host:
            [
                {
                    'ip': '192.168.1.1',
                    'open_ports': [80],
                    'closed_ports': [443, 22],
                    'scan_duration': 1.234
                },
                {
                    'ip': '192.168.1.2',
                    'open_ports': [80, 443],
                    'closed_ports': [22],
                    'scan_duration': 1.456
                }
            ]

        Example:
            >>> scanner = PortScanner()
            >>> hosts = ['192.168.1.1', '192.168.1.2', '192.168.1.3']
            >>> ports = [80, 443, 22]
            >>> results = scanner.scan_multiple_hosts(hosts, ports)
            >>>
            >>> for result in results:
            ...     print(f"{result['ip']}: {len(result['open_ports'])} open ports")
        """
        results = []

        try:
            for host in hosts:
                result = self.scan_host(host, ports)
                results.append(result)

        except Exception as e:
            self._logger.error(f"Error during multiple host scan: {e}")

        return results

    def _check_port(self, ip: str, port: int) -> bool:
        """
        Check if a single port is open on a host.

        Attempts to establish a TCP connection to the specified port.
        A successful connection (return code 0) indicates the port is open.

        Args:
            ip: IP address of the host
            port: Port number to check

        Returns:
            True if port is open (connection successful)
            False if port is closed (connection failed)

        Note:
            This is an internal method used by scan_host() and should not
            be called directly by external code.
        """
        sock = None
        try:
            # Create a TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Set timeout for connection attempt
            sock.settimeout(self.timeout)

            # Attempt to connect
            # connect_ex() returns 0 on success, error code otherwise
            result = sock.connect_ex((ip, port))

            # Return True if connection successful (result == 0)
            return result == 0

        except socket.timeout:
            # Timeout means port is filtered or host is down
            return False
        except socket.error:
            # Connection error means port is closed or unreachable
            return False
        except Exception as e:
            self._logger.error(f"Unexpected error checking {ip}:{port}: {e}")
            return False
        finally:
            # Always close the socket to free resources
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass  # Ignore errors during socket cleanup
