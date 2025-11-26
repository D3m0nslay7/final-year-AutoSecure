#!/usr/bin/env python3
"""
Discovery Engine Docker Wrapper
Runs the discovery engine and automatically detects the Docker bridge network
"""

import os
import sys

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from discovery_engine import DiscoveryEngine


def main():
    """Run discovery engine with Docker-optimized settings"""

    # Get scan duration from environment variable or use default
    duration = int(os.getenv('SCAN_DURATION', '10'))

    print("=" * 70)
    print(" " * 15 + "AutoSecure Discovery Engine")
    print(" " * 20 + "(Docker Edition)")
    print("=" * 70)
    print()
    print("Configuration:")
    print(f"  Scan Duration: {duration} seconds")
    print(f"  Network: Auto-detect (Docker bridge network)")
    print(f"  Methods: mDNS, SSDP, MQTT, ARP")
    print()
    print("=" * 70)

    # Create and run discovery engine
    engine = DiscoveryEngine()

    try:
        devices = engine.discover_all(duration=duration)
        engine.print_summary()

        # Export to JSON for easy parsing
        import json
        json_output = engine.export_devices(format='json')

        # Save to file if OUTPUT_FILE env var is set
        output_file = os.getenv('OUTPUT_FILE')
        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_output)
            print(f"\n✓ Results saved to: {output_file}")

    except KeyboardInterrupt:
        print("\n\nDiscovery interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during discovery: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
