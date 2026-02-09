# segmentation_engine.py
from .iptables_manager import IptablesManager
from .segment_config import SEGMENTS


class SegmentationEngine:
    def __init__(self):
        self.device_segments = {}  # {mac_address: segment_name}
        self.iptables_manager = IptablesManager()
    
    def classify_device(self, device_info):
        """Determine which segment based on discovery results"""
        protocols = device_info['protocols']
        
        if 'ssdp' in protocols or 'mdns' in protocols:
            return 'iot'
        elif 'mqtt' in protocols:
            return 'iot'
        elif 'coap' in protocols:
            return 'iot'
        else:
            return 'quarantine'  # Unknown devices isolated
    
    def apply_segmentation(self, device_info):
        """Apply iptables rules for this device"""
        mac = device_info['mac_address']
        ip = device_info['ip_address']
        segment = self.classify_device(device_info)
        
        # Track assignment
        self.device_segments[mac] = segment
        
        # Apply rules
        rules = SEGMENTS[segment]['rules']
        self.iptables_manager.apply_rules(ip, mac, rules)
        
        print(f"✓ Device {ip} ({mac}) → {segment.upper()} segment")