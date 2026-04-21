# main.py - orchestration
import subprocess
import time
from Discovery import DiscoveryEngine
from Segmentation.segmentation_engine import SegmentationEngine
from Monitoring.monitoring_engine import MonitoringEngine

MONITORING_DURATION = 60   # seconds per monitoring window
REDISCOVERY_INTERVAL = 5   # re-run discovery every N monitoring cycles


def run_discovery_and_segmentation():
    scanner = DiscoveryEngine()
    segmentation = SegmentationEngine()

    print("=" * 60)
    print("Discovery Phase")
    print("=" * 60)
    devices = scanner.discover_all()

    print("\n" + "=" * 60)
    print("Segmentation Phase")
    print("=" * 60)
    for device in devices.values():
        segmentation.apply_segmentation(device)

    print("\nActive iptables rules:")
    subprocess.run(['iptables', '-L', 'AUTOSECURE_IOT', '-n', '-v'], check=False)
    subprocess.run(['iptables', '-L', 'AUTOSECURE_QUARANTINE', '-n', '-v'], check=False)

    return devices, segmentation.device_segments


def run_autosecure():
    print("=" * 60)
    print("  AutoSecure - Continuous Monitoring Mode")
    print(f"  Monitoring window : {MONITORING_DURATION}s")
    print(f"  Re-discovery every: {REDISCOVERY_INTERVAL} cycle(s)")
    print("=" * 60 + "\n")

    devices, device_segments = run_discovery_and_segmentation()

    cycle = 1
    while True:
        print("\n" + "=" * 60)
        print(f"  Monitoring Cycle {cycle}  —  {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        monitoring = MonitoringEngine(devices, device_segments)
        monitoring.start(duration=MONITORING_DURATION)

        # Re-run discovery periodically to pick up new or changed devices
        if cycle % REDISCOVERY_INTERVAL == 0:
            print(f"\n[Cycle {cycle}] Re-running discovery to check for new devices...")
            devices, device_segments = run_discovery_and_segmentation()

        cycle += 1


if __name__ == "__main__":
    run_autosecure()