# Discovery Engine

A modular IoT device discovery system that supports multiple discovery methods.

## Architecture

```
discovery_engine.py  → Main orchestrator (coordinates all discovery methods)
    ↓ calls
mdns_module.py      → mDNS/Zeroconf discovery implementation
    ↓ returns
Device Dictionary   → Structured device data with IPs, MACs, metadata
```

## Quick Start

### Basic Usage

```python
from Engines.Discovery import DiscoveryEngine

# Create engine instance
engine = DiscoveryEngine()

# Discover devices for 15 seconds
devices = engine.discover_all(duration=15, methods=['mdns'])

# Access the devices dictionary
print(f"Found {len(devices)} devices")

# Print summary
engine.print_summary()
```

### Using mDNS Module Directly

```python
from Engines.Discovery import discover_mdns_devices

# Quick discovery
devices = discover_mdns_devices(duration=10)

# Each device has:
# {
#     'name': str,
#     'type': str,
#     'ip_address': str,
#     'mac_address': str or None,
#     'port': int,
#     'server': str,
#     'properties': dict,
#     'discovery_method': 'mdns'
# }
```

## Features

### Discovery Engine Methods

```python
engine = DiscoveryEngine()

# Discover all devices
devices = engine.discover_all(duration=15)

# Get all devices
all_devices = engine.get_all_devices()

# Query by IP
device = engine.get_device_by_ip('192.168.1.100')

# Query by MAC
device = engine.get_device_by_mac('AA:BB:CC:DD:EE:FF')

# Query by type
homekit_devices = engine.get_devices_by_type('_hap._tcp.local.')

# Print summary
engine.print_summary()

# Export devices
json_str = engine.export_devices(format='json')
```

### Device Data Structure

Each discovered device contains:

```python
{
    'id': 'device_identifier',
    'name': 'Device Name',
    'type': '_hap._tcp.local.',  # Service type
    'ip_address': '192.168.1.100',
    'mac_address': 'AA:BB:CC:DD:EE:FF',  # May be None
    'port': 8080,
    'server': 'device-hostname.local.',
    'properties': {
        'key1': 'value1',
        'key2': 'value2'
    },
    'discovery_method': 'mdns'  # or ['mdns', 'arp'] if found by multiple methods
}
```

## Supported Discovery Methods

### Currently Implemented

- **mDNS/Zeroconf** (`'mdns'`)
  - Discovers devices broadcasting mDNS services
  - Supports HomeKit (`_hap._tcp.local.`)
  - Supports generic IoT HTTP devices (`_http._tcp.local.`)

### Planned

- **ARP Scanning** (`'arp'`) - Network-level device discovery
- **Nmap Scanning** (`'nmap'`) - Port scanning and OS detection
- **SSDP/UPnP** - Universal Plug and Play devices
- **Bluetooth LE** - BLE device discovery

## Examples

### Example 1: Discover and List All IPs

```python
from Engines.Discovery import DiscoveryEngine

engine = DiscoveryEngine()
devices = engine.discover_all(duration=10)

# Get all IP addresses
ips = [d['ip_address'] for d in devices.values() if d.get('ip_address')]
print(f"Discovered IPs: {ips}")
```

### Example 2: Find HomeKit Devices

```python
from Engines.Discovery import DiscoveryEngine

engine = DiscoveryEngine()
engine.discover_all(duration=15)

# Get only HomeKit devices
homekit = engine.get_devices_by_type('_hap._tcp.local.')

for device in homekit:
    print(f"HomeKit Device: {device['name']} at {device['ip_address']}")
```

### Example 3: Continuous Monitoring

```python
from Engines.Discovery.mdns_module import MDNSDiscovery
import time

discovery = MDNSDiscovery()

# Start discovery (non-blocking setup)
discovery.zeroconf = Zeroconf()
discovery.listener = IoTDeviceListener()

# Browse services
for service_type in discovery.service_types:
    ServiceBrowser(discovery.zeroconf, service_type, discovery.listener)

# Monitor for 60 seconds
for i in range(60):
    time.sleep(1)
    current_devices = discovery.get_current_devices()
    print(f"Devices found so far: {len(current_devices)}")

discovery.stop_discovery()
```

## Running the Examples

```bash
# Run the example usage script
cd "Engines/Discovery"
python example_usage.py

# Or run the mdns_module directly
python mdns_module.py

# Or run the discovery_engine directly
python discovery_engine.py
```

## Requirements

```
zeroconf>=0.131.0
```

Install with:
```bash
pip install zeroconf
```

## TODO

- [ ] Implement MAC address lookup via ARP table
- [ ] Add ARP scanning discovery method
- [ ] Add Nmap integration
- [ ] Implement CSV export
- [ ] Add device persistence/caching
- [ ] Add async/threaded discovery for faster scanning
- [ ] Add device fingerprinting
- [ ] Add vulnerability detection integration
