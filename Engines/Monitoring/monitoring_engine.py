# monitoring_engine.py
import time
from collections import defaultdict
from scapy.all import sniff, ARP, Ether, IP, TCP


class MonitoringEngine:
    def __init__(self, devices, device_segments):
        """
        Args:
            devices: Dict of {device_id: device_info} from DiscoveryEngine
            device_segments: Dict of {mac_address: segment_name} from SegmentationEngine
        """
        self.device_segments = device_segments

        # Build lookup tables from discovered devices
        self.known_macs = {}   # {mac: device_info}
        self.known_ips = {}    # {ip: device_info}
        self.ip_to_mac = {}    # {ip: mac} for ARP spoof detection

        for device_info in devices.values():
            mac = device_info.get('mac_address')
            ip = device_info.get('ip_address')
            if mac:
                self.known_macs[mac] = device_info
            if ip:
                self.known_ips[ip] = device_info
            if ip and mac:
                self.ip_to_mac[ip] = mac

        self.alerts = []
        self.seen_alerts = set()       # (type, src) — deduplication key
        self.suppressed_counts = defaultdict(int)

        # Port scan state: {src_ip: set of dst_ports seen in current window}
        self.port_scan_tracker = defaultdict(set)
        self.port_scan_timestamps = defaultdict(float)

        print(f"  Monitoring {len(self.known_macs)} known devices across "
              f"{len(set(device_segments.values()))} segment(s)")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self, duration=60):
        print(f"  Sniffing traffic for {duration} seconds...")
        print("  Waiting for packets...\n")
        sniff(prn=self._inspect_packet, store=False, timeout=duration)
        self._print_summary()

    # ------------------------------------------------------------------
    # Packet inspection
    # ------------------------------------------------------------------

    def _inspect_packet(self, packet):
        self._check_unknown_device(packet)
        self._check_arp_spoof(packet)
        self._check_unencrypted_mqtt(packet)
        self._check_policy_violation(packet)
        self._check_port_scan(packet)

    def _check_unknown_device(self, packet):
        if Ether not in packet:
            return
        src_mac = packet[Ether].src
        if src_mac in ('ff:ff:ff:ff:ff:ff', '00:00:00:00:00:00'):
            return
        if src_mac not in self.known_macs:
            src_ip = packet[IP].src if IP in packet else 'unknown IP'
            self._alert('UNKNOWN_DEVICE', src_mac,
                        f"Packet from unrecognised device MAC {src_mac} (IP: {src_ip})")

    def _check_arp_spoof(self, packet):
        if ARP not in packet or packet[ARP].op != 2:  # op 2 = ARP reply
            return
        ip = packet[ARP].psrc
        mac = packet[ARP].hwsrc
        if ip in self.ip_to_mac and self.ip_to_mac[ip] != mac:
            self._alert('ARP_SPOOF', ip,
                        f"ARP spoofing detected: {ip} claimed by {mac}, "
                        f"expected {self.ip_to_mac[ip]}")

    def _check_unencrypted_mqtt(self, packet):
        if IP not in packet or TCP not in packet:
            return
        if packet[TCP].dport == 1883 or packet[TCP].sport == 1883:
            src = packet[IP].src
            self._alert('UNENCRYPTED_MQTT', src,
                        f"Unencrypted MQTT (port 1883) from {src} — use port 8883 for TLS")

    def _check_policy_violation(self, packet):
        if IP not in packet or Ether not in packet:
            return
        src_mac = packet[Ether].src
        src_ip = packet[IP].src
        dst_ip = packet[IP].dst
        segment = self.device_segments.get(src_mac)

        if segment == 'iot':
            # IOT devices must not access other internal devices
            if dst_ip in self.known_ips and dst_ip != src_ip:
                self._alert('POLICY_VIOLATION', src_ip,
                            f"IOT device {src_ip} ({src_mac}) accessing "
                            f"internal device {dst_ip} — blocked by policy")

        elif segment == 'quarantine':
            # Quarantine devices must not access anything outside known internal IPs
            if dst_ip not in self.known_ips:
                self._alert('POLICY_VIOLATION', src_ip,
                            f"Quarantined device {src_ip} ({src_mac}) attempting "
                            f"external access to {dst_ip} — blocked by policy")

    def _check_port_scan(self, packet):
        if IP not in packet or TCP not in packet:
            return
        if packet[TCP].flags != 0x02:  # SYN only
            return
        src_ip = packet[IP].src
        dst_port = packet[TCP].dport
        now = time.time()

        # Reset window after 10 seconds of inactivity
        if now - self.port_scan_timestamps[src_ip] > 10:
            self.port_scan_tracker[src_ip] = set()
            self.port_scan_timestamps[src_ip] = now

        self.port_scan_tracker[src_ip].add(dst_port)

        if len(self.port_scan_tracker[src_ip]) > 10:
            count = len(self.port_scan_tracker[src_ip])
            self._alert('PORT_SCAN', src_ip,
                        f"Possible port scan from {src_ip}: "
                        f"{count} distinct ports probed in 10 seconds")
            self.port_scan_tracker[src_ip] = set()  # Reset to avoid repeated alerts

    # ------------------------------------------------------------------
    # Alert helpers
    # ------------------------------------------------------------------

    def _alert(self, alert_type, src, message):
        dedup_key = (alert_type, src)
        if dedup_key in self.seen_alerts:
            self.suppressed_counts[dedup_key] += 1
            return
        self.seen_alerts.add(dedup_key)

        timestamp = time.strftime('%H:%M:%S')
        entry = {'time': timestamp, 'type': alert_type, 'message': message}
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
