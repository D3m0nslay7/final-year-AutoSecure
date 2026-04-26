# monitoring_engine.py


import time
import subprocess
import threading
import re
from collections import defaultdict


CONTAINER_NAME_PREFIXES = [
    "autosecure-mdns-generic-",
    "autosecure-mdns-homekit-",
    "autosecure-ssdp-generic-",
    "autosecure-mqtt-mosquitto-",
    "autosecure-mqtt-hivemq-",
    "autosecure-mqtt-emqx-",
]


def _get_container_name_for_ip(ip):
    """Ask Docker which autosecure device container has this IP."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None
        for name in result.stdout.strip().splitlines():
            if not any(name.startswith(p) for p in CONTAINER_NAME_PREFIXES):
                continue
            ip_result = subprocess.run(
                ["docker", "inspect", "--format",
                 "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", name],
                capture_output=True, text=True, timeout=5
            )
            if ip_result.stdout.strip() == ip:
                return name
    except Exception:
        pass
    return None


class MonitoringEngine:
    def __init__(self, devices, device_segments):
        """
        Args:
            devices: Dict of {device_id: device_info} from DiscoveryEngine
            device_segments: Dict of {mac_address: segment_name} from SegmentationEngine
        """
        self.device_segments = device_segments

        self.known_macs = {}   # {mac: device_info}
        self.known_ips  = {}   # {ip: device_info}
        self.ip_to_mac  = {}   # {ip: mac}
        self.ip_to_container = {}  # {ip: container_name}

        for device_info in devices.values():
            mac = device_info.get('mac_address')
            ip  = device_info.get('ip_address')
            if mac:
                self.known_macs[mac] = device_info
            if ip:
                self.known_ips[ip] = device_info
            if ip and mac:
                self.ip_to_mac[ip] = mac

        self.alerts = []
        self.seen_alerts       = set()
        self.suppressed_counts = defaultdict(int)
        self._lock = threading.Lock()

        self.port_scan_tracker    = defaultdict(set)
        self.port_scan_timestamps = defaultdict(float)

        print(f"  Monitoring {len(self.known_macs)} known devices across "
              f"{len(set(device_segments.values()))} segment(s)")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self, duration=60):
        print(f"  Sniffing traffic for {duration} seconds via docker exec tcpdump...")
        print("  Waiting for packets...\n")

        # Resolve container names for all known device IPs
        for ip in list(self.known_ips.keys()):
            name = _get_container_name_for_ip(ip)
            if name:
                self.ip_to_container[ip] = name

        print(f"  Resolved {len(self.ip_to_container)} device container(s): "
              f"{list(self.ip_to_container.values())}")

        if not self.ip_to_container:
            print("  WARNING: No device containers resolved — no traffic will be captured.")

        threads = []
        for ip, container in self.ip_to_container.items():
            t = threading.Thread(
                target=self._sniff_container,
                args=(container, ip, duration),
                daemon=True
            )
            t.start()
            threads.append(t)

        deadline = time.time() + duration + 5

        if threads:
            for t in threads:
                remaining = max(0, deadline - time.time())
                t.join(timeout=remaining)
        else:
            # No containers to sniff — still wait the full window so the
            # monitoring loop doesn't spin instantly between cycles
            remaining = max(0, deadline - time.time())
            time.sleep(remaining)

        self._print_summary()

    # ------------------------------------------------------------------
    # Per-container tcpdump thread
    # ------------------------------------------------------------------

    def _sniff_container(self, container, container_ip, duration):
        """Run tcpdump inside the given container and parse each line."""
        cmd = [
            "docker", "exec", container,
            "tcpdump", "-l", "-n", "-tttt",
            "--immediate-mode",
            "-i", "eth0",
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
        except FileNotFoundError:
            print(f"  ERROR: 'docker' command not found. "
                  f"Ensure the Docker socket is mounted and docker.io is installed.")
            return
        except Exception as e:
            print(f"  ERROR starting tcpdump in {container}: {e}")
            return

        deadline = time.time() + duration
        try:
            for line in proc.stdout:
                if time.time() > deadline:
                    break
                self._parse_tcpdump_line(line.strip(), container_ip)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    # ------------------------------------------------------------------
    # tcpdump line parser
    # ------------------------------------------------------------------

    # 2024-01-01 12:00:00.000000 IP 172.x.x.x.PORT > 172.x.x.x.PORT: Flags [S]
    _TCP_RE = re.compile(
        r'IP (\d+\.\d+\.\d+\.\d+)\.(\d+) > (\d+\.\d+\.\d+\.\d+)\.(\d+): Flags \[([^\]]+)\]'
    )
    # 2024-01-01 12:00:00.000000 IP 172.x.x.x.PORT > 239.255.255.250.1900: UDP, length N
    _UDP_RE = re.compile(
        r'IP (\d+\.\d+\.\d+\.\d+)\.(\d+) > (\d+\.\d+\.\d+\.\d+)\.(\d+): UDP'
    )
    _ARP_RE = re.compile(
        r'ARP, Reply (\d+\.\d+\.\d+\.\d+) is-at ([0-9a-f:]{17})'
    )
    def _parse_tcpdump_line(self, line, container_ip):
        arp_m = self._ARP_RE.search(line)
        if arp_m:
            self._check_arp_spoof_raw(arp_m.group(1), arp_m.group(2))
            return

        udp_m = self._UDP_RE.search(line)
        if udp_m:
            src_ip   = udp_m.group(1)
            dst_port = int(udp_m.group(4))
            if dst_port == 1900:
                self._check_unknown_device(src_ip)
            return

        tcp_m = self._TCP_RE.search(line)
        if not tcp_m:
            return

        src_ip   = tcp_m.group(1)
        src_port = int(tcp_m.group(2))
        dst_ip   = tcp_m.group(3)
        dst_port = int(tcp_m.group(4))
        flags    = tcp_m.group(5).strip()

        self._check_unencrypted_mqtt_raw(src_ip, src_port, dst_ip, dst_port)
        self._check_policy_violation_raw(src_ip, dst_ip)

        if flags == 'S':
            self._check_port_scan_raw(src_ip, dst_port)

    # ------------------------------------------------------------------
    # Detection logic
    # ------------------------------------------------------------------

    def _check_unknown_device(self, src_ip):
        if src_ip not in self.known_ips:
            self._alert('UNKNOWN_DEVICE', src_ip,
                        f"Unknown device sending SSDP traffic from {src_ip} "
                        f"— not in discovered device list")

    def _check_arp_spoof_raw(self, ip, mac):
        if ip in self.ip_to_mac and self.ip_to_mac[ip] != mac:
            self._alert('ARP_SPOOF', ip,
                        f"ARP spoofing detected: {ip} claimed by {mac}, "
                        f"expected {self.ip_to_mac[ip]}")

    def _check_unencrypted_mqtt_raw(self, src_ip, src_port, dst_ip, dst_port):
        if dst_port == 1883 or src_port == 1883:
            self._alert('UNENCRYPTED_MQTT', src_ip,
                        f"Unencrypted MQTT (port 1883) from {src_ip} "
                        f"→ {dst_ip} — use port 8883 for TLS")

    def _check_policy_violation_raw(self, src_ip, dst_ip):
        mac     = self.ip_to_mac.get(src_ip)
        segment = self.device_segments.get(mac)

        if segment == 'iot':
            if dst_ip in self.known_ips and dst_ip != src_ip:
                self._alert('POLICY_VIOLATION', src_ip,
                            f"IOT device {src_ip} accessing internal "
                            f"device {dst_ip} — blocked by policy")
        elif segment == 'quarantine':
            if dst_ip not in self.known_ips:
                self._alert('POLICY_VIOLATION', src_ip,
                            f"Quarantined device {src_ip} attempting "
                            f"external access to {dst_ip} — blocked by policy")

    def _check_port_scan_raw(self, src_ip, dst_port):
        now = time.time()
        with self._lock:
            if now - self.port_scan_timestamps[src_ip] > 10:
                self.port_scan_tracker[src_ip]    = set()
                self.port_scan_timestamps[src_ip] = now
            self.port_scan_tracker[src_ip].add(dst_port)
            count = len(self.port_scan_tracker[src_ip])

        if count > 10:
            self._alert('PORT_SCAN', src_ip,
                        f"Possible port scan from {src_ip}: "
                        f"{count} distinct ports probed in 10 seconds")
            with self._lock:
                self.port_scan_tracker[src_ip] = set()

    # ------------------------------------------------------------------
    # Alert helpers
    # ------------------------------------------------------------------

    def _alert(self, alert_type, src, message):
        dedup_key = (alert_type, src)
        with self._lock:
            if dedup_key in self.seen_alerts:
                self.suppressed_counts[dedup_key] += 1
                return
            self.seen_alerts.add(dedup_key)

        timestamp = time.strftime('%H:%M:%S')
        entry = {'time': timestamp, 'raw_time': time.time(), 'type': alert_type, 'message': message}
        with self._lock:
            self.alerts.append(entry)
        print(f"  [{timestamp}] ALERT [{alert_type}]: {message}")

    def _print_summary(self):
        total_suppressed = sum(self.suppressed_counts.values())
        print("\n" + "=" * 60)
        print(f"Monitoring Complete")
        print(f"  Unique alerts : {len(self.alerts)}")
        if total_suppressed:
            print(f"  Suppressed duplicates: {total_suppressed}")
        print("=" * 60)

        if not self.alerts:
            print("  No suspicious activity detected.")
            return

        by_type = defaultdict(list)
        for alert in self.alerts:
            by_type[alert['type']].append(alert)

        for alert_type, entries in sorted(by_type.items()):
            print(f"\n  [{alert_type}] {len(entries)} unique source(s):")
            for e in entries[:5]:
                print(f"    {e['time']}: {e['message']}")
            if len(entries) > 5:
                print(f"    ... and {len(entries) - 5} more")
