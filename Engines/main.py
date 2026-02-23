# main.py - orchestration
from Discovery import DiscoveryEngine
from Segmentation.segmentation_engine import SegmentationEngine
from Monitoring.monitoring_engine import MonitoringEngine

def run_autosecure():
    scanner = DiscoveryEngine()
    segmentation = SegmentationEngine()
    
    print("Discovery Phase")
    devices = scanner.discover_all()
    
    print("\nSegmentation Phase")
    for device in devices.values():
        segmentation.apply_segmentation(device)
        
    print("\nActive iptables rules for both segments, AUTOSECURE_IOT and AUTOSECURE_QUARANTINE:")
    import subprocess
    subprocess.run(['iptables', '-L', 'AUTOSECURE_IOT', '-n', '-v'], check=False)
    subprocess.run(['iptables', '-L', 'AUTOSECURE_QUARANTINE', '-n', '-v'], check=False)

    print("\nMonitoring Phase")
    monitoring = MonitoringEngine(devices, segmentation.device_segments)
    monitoring.start(duration=60)

if __name__ == "__main__":
    run_autosecure()