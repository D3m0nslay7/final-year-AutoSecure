# Discovery Engine Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Application                         │
│                                                               │
│   (Uses DiscoveryEngine to find IoT devices)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ import DiscoveryEngine
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              discovery_engine.py                             │
│                                                               │
│  • Orchestrates all discovery methods                       │
│  • Maintains unified device registry                        │
│  • Handles device deduplication                             │
│  • Provides query methods (by IP, MAC, type)                │
│                                                               │
│  Methods:                                                    │
│    - discover_all()                                          │
│    - get_all_devices()                                       │
│    - get_device_by_ip()                                      │
│    - get_device_by_mac()                                     │
│    - get_devices_by_type()                                   │
│    - print_summary()                                         │
│    - export_devices()                                        │
└────────────┬───────────┬──────────────┬─────────────────────┘
             │           │              │
             │           │              │
    ┌────────▼──┐   ┌───▼──────┐   ┌──▼─────────┐
    │  mDNS     │   │   ARP    │   │   Nmap     │
    │  Module   │   │  Module  │   │   Module   │
    │           │   │  (TODO)  │   │   (TODO)   │
    └────┬──────┘   └──────────┘   └────────────┘
         │
         │ Calls discover_mdns_devices()
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    mdns_module.py                            │
│                                                               │
│  Classes:                                                    │
│    • IoTDeviceListener - Listens for mDNS broadcasts        │
│    • MDNSDiscovery - Manages discovery process              │
│                                                               │
│  Functions:                                                  │
│    • discover_mdns_devices() - Convenience function         │
│                                                               │
│  Discovers:                                                  │
│    - HomeKit devices (_hap._tcp.local.)                     │
│    - Generic IoT devices (_http._tcp.local.)                │
│    - Any mDNS/Zeroconf advertised service                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Returns device dictionary
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Device Dictionary                          │
│                                                               │
│  {                                                           │
│    'device_name': {                                          │
│      'name': 'My IoT Device',                                │
│      'type': '_hap._tcp.local.',                            │
│      'ip_address': '192.168.1.100',                         │
│      'mac_address': 'AA:BB:CC:DD:EE:FF',                    │
│      'port': 8080,                                           │
│      'server': 'device.local.',                             │
│      'properties': {...},                                    │
│      'discovery_method': 'mdns'                             │
│    }                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Discovery Process

```
User Code
    │
    ├─► engine = DiscoveryEngine()
    │
    └─► devices = engine.discover_all(duration=15, methods=['mdns'])
            │
            ├─► Calls _discover_mdns(15)
            │       │
            │       └─► discover_mdns_devices(duration=15)
            │               │
            │               ├─► Creates MDNSDiscovery instance
            │               │
            │               ├─► Starts Zeroconf/ServiceBrowser
            │               │
            │               ├─► Listens for broadcasts (15 seconds)
            │               │       │
            │               │       └─► IoTDeviceListener.add_service()
            │               │               │
            │               │               └─► Parses device info
            │               │                   - Extract IP
            │               │                   - Extract properties
            │               │                   - Attempt MAC lookup
            │               │
            │               └─► Returns {device_dict}
            │
            └─► _merge_devices(device_dict)
                    │
                    ├─► Check for duplicates by IP
                    │
                    ├─► Merge or add to registry
                    │
                    └─► Return unified device list
```

### 2. Querying Devices

```
User Code
    │
    ├─► all = engine.get_all_devices()
    │       └─► Returns copy of discovered_devices dict
    │
    ├─► device = engine.get_device_by_ip('192.168.1.100')
    │       └─► Searches registry by IP, returns device
    │
    ├─► device = engine.get_device_by_mac('AA:BB:CC:DD:EE:FF')
    │       └─► Searches registry by MAC, returns device
    │
    └─► devices = engine.get_devices_by_type('_hap._tcp.local.')
            └─► Filters registry by type, returns list
```

## Module Responsibilities

### discovery_engine.py

**Purpose:** High-level orchestrator and device registry

**Responsibilities:**
- Coordinate multiple discovery methods
- Maintain centralized device registry
- Deduplicate devices found by multiple methods
- Provide unified query interface
- Export functionality

**Key Classes:**
- `DiscoveryEngine` - Main coordinator class

### mdns_module.py

**Purpose:** mDNS/Zeroconf device discovery

**Responsibilities:**
- Listen for mDNS broadcasts
- Parse device information from Zeroconf
- Extract IPs, ports, properties
- Attempt MAC address resolution
- Return structured device data

**Key Classes:**
- `IoTDeviceListener` - ServiceListener implementation
- `MDNSDiscovery` - Discovery manager

**Key Functions:**
- `discover_mdns_devices()` - Convenience function

## Integration Example

```python
# In your main application
from Engines.Discovery import DiscoveryEngine

class AutoSecureApp:
    def __init__(self):
        self.discovery_engine = DiscoveryEngine()
        self.discovered_devices = {}

    def scan_network(self):
        """Scan network and populate device list"""
        print("Scanning network...")

        # Run discovery for 20 seconds
        self.discovered_devices = self.discovery_engine.discover_all(
            duration=20,
            methods=['mdns']  # Add 'arp', 'nmap' when available
        )

        print(f"Found {len(self.discovered_devices)} devices")
        return self.discovered_devices

    def get_device_info(self, ip_address):
        """Get detailed info for a specific device"""
        return self.discovery_engine.get_device_by_ip(ip_address)

    def list_vulnerable_devices(self):
        """Example: Find devices that might be vulnerable"""
        all_devices = self.discovery_engine.get_all_devices()

        vulnerable = []
        for device_id, device in all_devices.items():
            # Check for common vulnerable ports
            if device.get('port') in [23, 80, 8080]:
                vulnerable.append(device)

        return vulnerable
```

## Extension Points

### Adding New Discovery Methods

To add a new discovery method (e.g., ARP scanning):

1. Create `arp_module.py`:
```python
def discover_arp_devices() -> Dict:
    # Implementation
    return {
        'device_id': {
            'ip_address': '...',
            'mac_address': '...',
            'discovery_method': 'arp'
        }
    }
```

2. Add to `discovery_engine.py`:
```python
def _discover_arp(self) -> Dict:
    from .arp_module import discover_arp_devices
    return discover_arp_devices()

def discover_all(self, duration=10, methods=['mdns', 'arp']):
    # ...
    if 'arp' in methods:
        arp_devices = self._discover_arp()
        self._merge_devices(arp_devices)
```

3. Update `__init__.py` to export new module

## Future Enhancements

1. **Asynchronous Discovery**
   - Run multiple methods in parallel
   - Non-blocking discovery
   - Real-time device updates

2. **Device Fingerprinting**
   - OS detection
   - Service version detection
   - Device type classification

3. **Persistent Storage**
   - Cache discovered devices
   - Track device history
   - Monitor device changes

4. **Security Analysis Integration**
   - Vulnerability scanning
   - Default credential checking
   - Firmware version analysis
