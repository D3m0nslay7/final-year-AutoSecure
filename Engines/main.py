# main.py - orchestration
from Discovery import DiscoveryEngine
from Segmentation.segmentation_engine import SegmentationEngine

def run_autosecure():
    scanner = DiscoveryEngine()
    segmentation = SegmentationEngine()
    
    print("🔍 Phase 1: Discovery")
    devices = scanner.discover_all()
    
    print("\n🔒 Phase 2: Segmentation")
    for device in devices:
        segmentation.apply_segmentation(device)
    
    print("\n✅ AutoSecure active - monitoring traffic")

if __name__ == "__main__":
    run_autosecure()