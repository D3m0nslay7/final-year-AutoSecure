"""
MQTT Discovery Debug Test

This script enables debug logging to show exactly what's happening
during MQTT broker discovery.
"""

import logging
import sys
import os

# Enable DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s',
    stream=sys.stdout
)

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import modules directly (avoiding relative imports)
from modules.core.network_scanner import NetworkScanner
from modules.core.port_scanner import PortScanner
from modules.protocols.mqtt_detector import MQTTBrokerDetector
import socket
import ipaddress

def main():
    print("=" * 70)
    print("MQTT DISCOVERY DEBUG TEST")
    print("=" * 70)
    print()
    print("Running MQTT discovery with DEBUG logging enabled...")
    print("This will show exactly which ports are being scanned and found.")
    print()
    print("=" * 70)
    print()

    try:
        # Detect local subnet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        target_subnet = str(network)

        print(f"Scanning subnet: {target_subnet}\n")

        # Step 1: Scan network for devices
        print("[1/3] Scanning network for active devices...")
        net_scanner = NetworkScanner(target_subnet, timeout=5)
        devices = net_scanner.scan()
        print(f"Found {len(devices)} device(s) on network\n")

        # Step 2: Find MQTT brokers
        print("[2/3] Scanning for MQTT brokers...")
        port_scanner = PortScanner(timeout=2, max_workers=20)
        mqtt_detector = MQTTBrokerDetector(port_scanner, timeout=2)

        brokers = mqtt_detector.find_brokers(devices)

        print(f"\n[3/3] Processing results...")
        print()
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)

        if brokers:
            print(f"\nFound {len(brokers)} MQTT broker(s):\n")
            for broker in brokers:
                print(f"  ✓ {broker['vendor']}")
                print(f"    IP:      {broker['ip']}")
                print(f"    Port:    {broker['port']}")
                print(f"    Version: MQTT {broker['mqtt_version']}")
                print(f"    Features: {', '.join(broker['features']) if broker['features'] else 'None'}")
                if broker['additional_ports']:
                    print(f"    Other MQTT ports: {broker['additional_ports']}")
                print()
        else:
            print("\nNo MQTT brokers found.")

    except Exception as e:
        print(f"\nError during discovery: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
