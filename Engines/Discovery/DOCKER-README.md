## Discovery Engine - Docker Setup

Run the AutoSecure Discovery Engine in a Docker container on the **same network** as your test devices!

## Quick Start

### 1. Start Test Devices (if not already running)

```batch
cd ..\..\Devices
run-all-devices.bat
```

This starts all test devices on the Docker bridge network.

### 2. Run Discovery Engine

```batch
cd Engines\Discovery
run-discovery-engine.bat
```

The Discovery Engine will:
- ✅ Run in a Docker container
- ✅ Connect to the same bridge network as test devices
- ✅ Automatically detect and scan the Docker subnet
- ✅ Discover all mDNS, SSDP, and MQTT devices
- ✅ Display a summary of discovered devices

## How It Works

### Network Configuration

Both test devices and Discovery Engine run on Docker's **bridge network**:

```
Docker Bridge Network (172.17.0.0/16)
├── autosecure-mdns-generic-1 (172.17.0.2)
├── autosecure-mdns-generic-2 (172.17.0.3)
├── autosecure-mqtt-mosquitto-1 (172.17.0.4)
├── autosecure-ssdp-generic-1 (172.17.0.5)
└── autosecure-discovery-engine (172.17.0.6) ← Scans the network!
```

The Discovery Engine automatically:
1. Detects its own IP (e.g., `172.17.0.6`)
2. Determines the subnet (e.g., `172.17.0.0/24`)
3. Scans all IPs in that subnet
4. Discovers devices using mDNS, SSDP, MQTT, and ARP

### Capabilities Required

The Discovery Engine container runs with:
- `--cap-add=NET_ADMIN` - For ARP scanning
- `--cap-add=NET_RAW` - For raw socket access (network scanning)
- `--network bridge` - Connects to Docker's default bridge network

These capabilities allow the container to perform network discovery like it would on a physical network.

## Usage

### Basic Discovery (10 seconds)

```batch
run-discovery-engine.bat
```

### Custom Duration

```batch
run-discovery-custom.bat 30
```

This runs discovery for 30 seconds instead of the default 10.

### Save Results to File

```batch
docker run -it --rm ^
    --name autosecure-discovery-engine ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    -e OUTPUT_FILE=/app/results.json ^
    -v "%cd%":/output ^
    autosecure-discovery-engine
```

Results will be saved to `results.json` in the current directory.

## Expected Output

```
============================================================
Starting Device Discovery Engine
============================================================

[1/4] Running mDNS Discovery...
  Scanning for mDNS services...
  ✓ Found: GenericIoTDevice-1234 (Generic IoT Device)
  ✓ Found: SmartLight-5678 (HomeKit Device)
  Found 2 mDNS device(s)

[2/4] Running SSDP Discovery...
  Scanning for SSDP devices...
  ✓ Found: upnp:rootdevice at 172.17.0.5
  Found 1 SSDP device(s)

[3/4] Running MQTT Discovery...
  Scanning subnet: 172.17.0.0/24
  [1/3] Scanning network for active devices...
  Found 5 device(s) on network
  [2/3] Checking devices for MQTT brokers...
  ✓ Found: Mosquitto at 172.17.0.4:1883 (MQTT 3.1.1)
  [3/3] Processing 1 MQTT broker(s)...

[Enrichment] Using ARP to get MAC addresses for discovered devices...
  Querying 3 IP addresses...
  ✓ Got MAC for 172.17.0.2
  ✓ Got MAC for 172.17.0.3
  ✓ Got MAC for 172.17.0.4

============================================================
Discovery Complete - Total Devices: 4
============================================================

============================================================
DISCOVERED DEVICES SUMMARY (4 total)
============================================================

Device: GenericIoTDevice-1234
  IP Address:  172.17.0.2
  MAC Address: 02:42:ac:11:00:02
  Type:        _http._tcp.local.
  Port:        80
  Method:      mdns
  Properties:  4 item(s)

Device: SmartLight-5678
  IP Address:  172.17.0.3
  MAC Address: 02:42:ac:11:00:03
  Type:        _hap._tcp.local.
  Port:        8080
  Method:      mdns
  Properties:  8 item(s)

Device: upnp:rootdevice
  IP Address:  172.17.0.5
  MAC Address: 02:42:ac:11:00:05
  Type:        upnp:rootdevice
  Port:        8234
  Method:      ssdp

Device: Mosquitto MQTT Broker
  IP Address:  172.17.0.4
  MAC Address: 02:42:ac:11:00:04
  Type:        mqtt_broker
  Port:        1883
  Method:      mqtt
  Properties:  3 item(s)

============================================================
```

## Troubleshooting

### No Devices Found

**Problem:** Discovery Engine finds 0 devices

**Solutions:**

1. **Check that test devices are running:**
   ```batch
   docker ps --filter name=autosecure-
   ```
   You should see your device containers running.

2. **Verify network connectivity:**
   ```batch
   # Get Discovery Engine IP
   docker inspect autosecure-discovery-engine | findstr IPAddress

   # Get test device IPs
   docker inspect autosecure-mdns-generic-1 | findstr IPAddress
   ```

3. **Check they're on the same network:**
   Both should have IPs in the `172.17.0.0/16` range.

4. **Increase scan duration:**
   ```batch
   run-discovery-custom.bat 30
   ```
   Give it more time to discover devices.

### Permission Denied Errors

**Problem:** `PermissionError: Operation not permitted`

**Solution:** The container needs elevated capabilities. The run script includes `--cap-add=NET_ADMIN` and `--cap-add=NET_RAW`, which should handle this.

If you're running manually:
```batch
docker run --cap-add=NET_ADMIN --cap-add=NET_RAW ...
```

### Discovery Engine Can't Find Docker Network

**Problem:** Discovery Engine scans wrong subnet

**Solution:** The engine auto-detects the subnet, but you can override it:

```batch
docker run -it --rm ^
    --name autosecure-discovery-engine ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    -e FORCE_SUBNET=172.17.0.0/24 ^
    autosecure-discovery-engine
```

### Only MQTT Devices Found (No mDNS/SSDP)

**Problem:** mDNS and SSDP use multicast, which may have issues in Docker

**Explanation:** Docker's default bridge network doesn't always support multicast well. mDNS and SSDP discovery might not work.

**Solutions:**

1. **Use host network mode** (Discovery Engine can see host's network directly):
   ```batch
   docker run -it --rm ^
       --name autosecure-discovery-engine ^
       --network host ^
       autosecure-discovery-engine
   ```
   **Note:** Test devices must also use host network mode.

2. **Create a custom network with multicast support:**
   ```batch
   docker network create --driver bridge --opt com.docker.network.bridge.enable_ip_masquerade=true autosecure-net
   ```
   Then run all containers on `autosecure-net` network.

## Advanced Usage

### Run Discovery Engine Interactively

```batch
docker run -it --rm ^
    --name autosecure-discovery-engine ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    autosecure-discovery-engine /bin/bash
```

Then inside the container:
```bash
python discovery_engine.py
```

### View Container Logs

```batch
# In detached mode
docker run -d --name autosecure-discovery-engine ...

# View logs
docker logs -f autosecure-discovery-engine
```

### Export Results

```batch
docker run -it --rm ^
    --name autosecure-discovery-engine ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    -e OUTPUT_FILE=/results/devices.json ^
    -v "%cd%\results":/results ^
    autosecure-discovery-engine
```

Results saved to `results\devices.json` on your host.

## Complete Workflow Example

### 1. Start Test Devices

```batch
cd ..\..\Devices

# Start 5 Generic IoT devices
cd mDNS
run-generic.bat 5

# Start 3 SSDP devices
cd ..\SSDP
run-generic.bat 3

# Start MQTT brokers
cd ..\MQTT
run-mosquitto.bat 1
run-hivemq.bat 1
```

**Total: 10 devices running**

### 2. Verify Devices Are Running

```batch
cd ..\..
list-devices.bat
```

### 3. Run Discovery Engine

```batch
cd Engines\Discovery
run-discovery-engine.bat
```

### 4. View Results

The Discovery Engine should find all 10 devices with their IPs, MACs, and details.

### 5. Stop Everything

```batch
cd ..\..\Devices
stop-all-devices.bat
```

## File Structure

```
Engines/Discovery/
├── Dockerfile                      # Discovery Engine container
├── requirements.txt                # Python dependencies
├── run_discovery_docker.py         # Docker wrapper script
├── discovery_engine.py             # Main discovery engine
├── run-discovery-engine.bat        # Run Discovery Engine (10s)
├── run-discovery-custom.bat        # Run with custom duration
├── DOCKER-README.md                # This file
└── modules/                        # Discovery modules
    ├── core/
    │   ├── network_scanner.py
    │   └── port_scanner.py
    └── protocols/
        ├── mdns_module.py
        ├── ssdp_module.py
        ├── mqtt_detector.py
        └── arp_module.py
```

## Dependencies

Installed automatically in the Docker image:
- `zeroconf` - mDNS/Zeroconf discovery
- `ssdpy` - SSDP/UPnP discovery
- `scapy` - Network/ARP scanning
- `requests` - HTTP requests for MQTT broker detection
- `paho-mqtt` - MQTT protocol support

## Next Steps

1. Start test devices: `cd Devices && run-all-devices.bat`
2. Run discovery: `cd Engines\Discovery && run-discovery-engine.bat`
3. Experiment with different device counts and types
4. Export results for analysis

Enjoy discovering your IoT devices! 🚀
