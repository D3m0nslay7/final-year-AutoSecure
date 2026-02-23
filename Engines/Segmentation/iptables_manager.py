# iptables_manager.py
import subprocess

class IptablesManager:
    def __init__(self):
        self.initialize_chains()

    def initialize_chains(self):
        """Create custom chains for AutoSecure"""
        subprocess.run(['iptables', '-N', 'AUTOSECURE_IOT'], check=False)
        subprocess.run(['iptables', '-N', 'AUTOSECURE_TRUSTED'], check=False)
        subprocess.run(['iptables', '-N', 'AUTOSECURE_QUARANTINE'], check=False)

        # Forward all traffic through AutoSecure chains
        subprocess.run([
            'iptables', '-A', 'FORWARD',
            '-j', 'AUTOSECURE_IOT'
        ])

    def apply_rules(self, ip, mac, rules):
        """Apply segment-specific rules"""

        if rules['block_internal']:
            # Allow gateway first, then block rest of internal network (two rules required)
            subprocess.run([
                'iptables', '-A', 'AUTOSECURE_IOT',
                '-s', ip,
                '-d', '192.168.1.1',
                '-j', 'ACCEPT'
            ], check=False)
            subprocess.run([
                'iptables', '-A', 'AUTOSECURE_IOT',
                '-s', ip,
                '-d', '192.168.1.0/24',
                '-j', 'DROP'
            ], check=False)

        if not rules['allow_internet']:
            # Block all external access
            subprocess.run([
                'iptables', '-A', 'AUTOSECURE_QUARANTINE',
                '-s', ip,
                '!', '-d', '192.168.1.0/24',
                '-j', 'DROP'
            ])

        if rules['allow_ports']:
            # Whitelist specific ports only
            for port in rules['allow_ports']:
                subprocess.run([
                    'iptables', '-A', 'AUTOSECURE_IOT',
                    '-s', ip,
                    '-p', 'tcp',
                    '--dport', str(port),
                    '-j', 'ACCEPT'
                ])

    def clear_device_rules(self, ip):
        """Remove all rules for a device (for re-segmentation)"""
        subprocess.run([
            'iptables', '-D', 'AUTOSECURE_IOT',
            '-s', ip
        ], check=False)
