"""
Quick test script to verify the Discovery Engine setup
Run this to make sure everything is working correctly
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import Engines
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from Engines.Discovery import DiscoveryEngine
        from Engines.Discovery.modules import (
            discover_mdns_devices,
            MDNSDiscovery,
            IoTDeviceListener,
        )

        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_basic_discovery():
    """Test basic discovery functionality"""
    print("\nTesting basic discovery (5 seconds)...")
    try:
        from Engines.Discovery import DiscoveryEngine

        engine = DiscoveryEngine()
        devices = engine.discover_all(duration=5, methods=["mdns"])

        print(f"✓ Discovery completed")
        print(f"  Found {len(devices)} device(s)")

        if devices:
            print("\nDevice summary:")
            for device_id, device in devices.items():
                print(f"  - {device.get('name', device_id)}")
                print(f"    IP: {device.get('ip_address', 'Unknown')}")
                print(f"    Type: {device.get('type', 'Unknown')}")
        else:
            print("\n  Note: No devices found. This is normal if there are no")
            print("  mDNS-enabled devices on your network.")

        return True
    except Exception as e:
        print(f"✗ Discovery error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_query_methods():
    """Test device query methods"""
    print("\nTesting query methods...")
    try:
        from Engines.Discovery import DiscoveryEngine

        engine = DiscoveryEngine()
        devices = engine.discover_all(duration=5, methods=["mdns"])

        # Test get_all_devices
        all_devices = engine.get_all_devices()
        print(f"✓ get_all_devices(): {len(all_devices)} devices")

        if all_devices:
            # Test get_device_by_ip
            first_device = list(all_devices.values())[0]
            test_ip = first_device.get("ip_address")

            if test_ip:
                found = engine.get_device_by_ip(test_ip)
                if found:
                    print(f"✓ get_device_by_ip('{test_ip}'): Found")
                else:
                    print(f"✗ get_device_by_ip('{test_ip}'): Not found")

            # Test get_devices_by_type
            homekit = engine.get_devices_by_type("_hap._tcp.local.")
            print(f"✓ get_devices_by_type('_hap._tcp.local.'): {len(homekit)} devices")

        return True
    except Exception as e:
        print(f"✗ Query error: {e}")
        return False


def test_mdns_module_directly():
    """Test mdns_module directly"""
    print("\nTesting mdns_module directly (3 seconds)...")
    try:
        from Engines.Discovery.modules.mdns_module import discover_mdns_devices

        devices = discover_mdns_devices(duration=3)
        print(f"✓ discover_mdns_devices() completed")
        print(f"  Found {len(devices)} device(s)")

        return True
    except Exception as e:
        print(f"✗ mDNS module error: {e}")
        return False


def main():
    print("=" * 70)
    print("Discovery Engine - Quick Test Suite")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Import Test", test_imports()))
    results.append(("mDNS Module Test", test_mdns_module_directly()))
    results.append(("Basic Discovery Test", test_basic_discovery()))
    results.append(("Query Methods Test", test_query_methods()))

    # Print results
    print("\n" + "=" * 70)
    print("Test Results")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n✓ All tests passed! The Discovery Engine is working correctly.")
        print("\nUsage in your code:")
        print("  from Engines.Discovery import DiscoveryEngine")
        print("  engine = DiscoveryEngine()")
        print("  devices = engine.discover_all(duration=15)")
    else:
        print("\n✗ Some tests failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("  1. Make sure 'zeroconf' is installed: pip install zeroconf")
        print("  2. Check that you're in the Engines/Discovery directory")
        print("  3. Verify no firewall is blocking mDNS (port 5353)")

    print()


if __name__ == "__main__":
    main()
