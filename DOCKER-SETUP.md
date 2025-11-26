# AutoSecure - Docker Testing Environment

Complete Docker-based setup for testing IoT device discovery with realistic network simulation.

## Overview

This project provides:
- **Test Devices** (mDNS, SSDP, MQTT) running in separate Docker containers
- **Discovery Engine** running in a Docker container on the same network
- **Multi-instance support** - Run 1, 5, 10, or 100+ devices for stress testing
- **Realistic network simulation** - Each container gets unique IP and MAC addresses

## Quick Start

### One-Command Setup

```batch
run-complete-test.bat
```

This will:
1. Start 9 test devices (mDNS, SSDP, MQTT)
2. Run the Discovery Engine
3. Display all discovered devices

### Manual Setup

#### 1. Start Test Devices

```batch
cd Devices
run-all-devices.bat
```

#### 2. Run Discovery Engine

```batch
cd Engines\Discovery
run-discovery-engine.bat
```

#### 3. Stop Everything

```batch
cd Devices
stop-all-devices.bat
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Docker Bridge Network (172.17.0.0/16)           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Test Devices (Separate Containers)                     │
│  ├─ autosecure-mdns-generic-1    (172.17.0.2)          │
│  ├─ autosecure-mdns-generic-2    (172.17.0.3)          │
│  ├─ autosecure-mdns-homekit-1    (172.17.0.4)          │
│  ├─ autosecure-mdns-homekit-2    (172.17.0.5)          │
│  ├─ autosecure-ssdp-generic-1    (172.17.0.6)          │
│  ├─ autosecure-ssdp-generic-2    (172.17.0.7)          │
│  ├─ autosecure-mqtt-mosquitto-1  (172.17.0.8)          │
│  ├─ autosecure-mqtt-hivemq-1     (172.17.0.9)          │
│  └─ autosecure-mqtt-emqx-1       (172.17.0.10)         │
│                                                          │
│  Discovery Engine                                       │
│  └─ autosecure-discovery-engine  (172.17.0.11)         │
│     └─ Scans 172.17.0.0/16 → Finds all devices!        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Multiple Instances

Run the same device type multiple times:

```batch
cd Devices\mDNS
run-generic.bat 10      # 10 Generic IoT devices

cd ..\SSDP
run-generic.bat 5       # 5 SSDP devices
```

Each instance gets:
- ✅ Unique container name
- ✅ Unique IP address
- ✅ Unique MAC address
- ✅ Unique device ID

### 2. Separate Network Devices

Each Docker container appears as a separate device:
- Own network interface
- Own IP/MAC addresses
- Isolated from other containers

Perfect for realistic IoT testing!

### 3. Protocol Support

**mDNS Devices:**
- Generic IoT Device (`_http._tcp.local.`)
- HomeKit Smart Light (`_hap._tcp.local.`)

**SSDP Devices:**
- Generic UPnP devices (MediaRenderer, MediaServer, Basic)

**MQTT Brokers:**
- Mosquitto (port 1883)
- HiveMQ (port 8883 + Web UI 8000)
- EMQX (port 8884 + Dashboard 18083)

### 4. Discovery Engine

Runs all discovery methods:
- ✅ mDNS/Zeroconf discovery
- ✅ SSDP/UPnP discovery
- ✅ MQTT broker detection
- ✅ ARP scanning for MAC addresses

## Project Structure

```
final-year-AutoSecure/
├── run-complete-test.bat           # Master script (devices + discovery)
│
├── Devices/                        # Test device containers
│   ├── run-all-devices.bat         # Start all devices (default config)
│   ├── stop-all-devices.bat        # Stop all devices
│   ├── list-devices.bat            # List running devices
│   │
│   ├── mDNS/
│   │   ├── Dockerfile
│   │   ├── run-generic.bat         # Run Generic IoT (supports N instances)
│   │   └── run-homekit.bat         # Run HomeKit (supports N instances)
│   │
│   ├── SSDP/
│   │   ├── Dockerfile
│   │   └── run-generic.bat         # Run SSDP (supports N instances)
│   │
│   └── MQTT/
│       ├── Dockerfile
│       ├── run-mosquitto.bat       # Run Mosquitto (supports N instances)
│       ├── run-hivemq.bat          # Run HiveMQ (supports N instances)
│       └── run-emqx.bat            # Run EMQX (supports N instances)
│
└── Engines/
    └── Discovery/                  # Discovery Engine container
        ├── Dockerfile
        ├── run-discovery-engine.bat    # Run discovery (10s scan)
        ├── run-discovery-custom.bat    # Run with custom duration
        └── DOCKER-README.md            # Detailed documentation
```

## Usage Examples

### Example 1: Basic Discovery Test

```batch
# Start default devices (9 total)
cd Devices
run-all-devices.bat

# Run discovery
cd ..\Engines\Discovery
run-discovery-engine.bat

# Should find all 9 devices
```

### Example 2: Stress Test with 50 Devices

```batch
cd Devices\mDNS
run-generic.bat 20

cd ..\SSDP
run-generic.bat 20

cd ..\MQTT
run-mosquitto.bat 10

# Total: 50 devices

cd ..\..\Engines\Discovery
run-discovery-custom.bat 30    # 30-second scan
```

### Example 3: Protocol-Specific Testing

```batch
# Test only MQTT discovery
cd Devices\MQTT
run-mosquitto.bat 3
run-hivemq.bat 2
run-emqx.bat 1

cd ..\..\Engines\Discovery
run-discovery-engine.bat
```

## How It Works

### Container Networking

1. **Docker Bridge Network**: All containers connect to Docker's default bridge network (`172.17.0.0/16`)

2. **Automatic IP Assignment**: Docker assigns each container a unique IP (172.17.0.2, 172.17.0.3, etc.)

3. **Unique MAC Addresses**: Docker generates unique MAC addresses for each container

4. **Network Discovery**: The Discovery Engine scans the bridge network and finds all device containers

### Discovery Process

1. **mDNS Discovery**: Listens for multicast mDNS broadcasts
2. **SSDP Discovery**: Sends SSDP M-SEARCH queries and receives responses
3. **MQTT Discovery**: Scans network IPs for MQTT ports (1883, 8883, 8884) and verifies protocol
4. **ARP Enrichment**: Uses ARP to get MAC addresses for discovered devices

## Management

### View Logs

```batch
# View logs for specific device
docker logs autosecure-mdns-generic-1

# Follow logs in real-time
docker logs -f autosecure-mqtt-mosquitto-1
```

### Check Container Status

```batch
# List all AutoSecure containers
docker ps --filter name=autosecure-

# Check specific container details
docker inspect autosecure-mdns-generic-1
```

### Stop Specific Devices

```batch
# Stop single device
docker stop autosecure-mdns-generic-1

# Stop all Generic IoT devices
docker stop $(docker ps -q --filter name=autosecure-mdns-generic)

# Stop ALL AutoSecure containers
cd Devices
stop-all-devices.bat
```

### Clean Up

```batch
# Remove stopped containers
docker container prune

# Remove AutoSecure images
docker rmi autosecure-mdns-generic autosecure-ssdp-generic autosecure-mqtt-mosquitto
```

## Troubleshooting

### Docker Not Running

**Error:** `error during connect: ... docker daemon is not running`

**Solution:** Start Docker Desktop and wait for it to fully initialize

### No Devices Found

**Problem:** Discovery Engine finds 0 devices

**Solutions:**
1. Check devices are running: `docker ps --filter name=autosecure-`
2. Increase scan duration: `run-discovery-custom.bat 30`
3. Verify network: Both should be on bridge network

### Port Already in Use

**Problem:** `port is already allocated`

**Solution:** Stop conflicting containers or use different ports:
```batch
docker stop $(docker ps -q --filter publish=1883)
```

### Build Failures

**Problem:** Docker build fails

**Solutions:**
1. Check Docker has internet access (needs to pull base images)
2. Clear Docker cache: `docker system prune -a`
3. Rebuild with no cache: `docker build --no-cache ...`

## Advanced Usage

### Custom Network

Create a custom network for better isolation:

```batch
# Create network
docker network create --driver bridge autosecure-network

# Run devices on custom network
docker run --network autosecure-network ...

# Run discovery engine on same network
docker run --network autosecure-network ...
```

### Export Discovery Results

```batch
docker run --rm ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    -e OUTPUT_FILE=/results/devices.json ^
    -v "%cd%\results":/results ^
    autosecure-discovery-engine
```

Results saved to `results\devices.json`

### Interactive Mode

```batch
# Run discovery engine interactively
docker run -it --rm ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    autosecure-discovery-engine /bin/bash

# Inside container
python discovery_engine.py
```

## Requirements

- Docker Desktop installed and running
- Windows 10/11 (for .bat scripts)
- At least 2GB RAM for Docker
- 5GB disk space for images

## Documentation

- **[Devices/README.md](Devices/README.md)** - Complete device documentation
- **[Devices/QUICK-START.md](Devices/QUICK-START.md)** - Device quick start guide
- **[Engines/Discovery/DOCKER-README.md](Engines/Discovery/DOCKER-README.md)** - Discovery Engine documentation
- **[Engines/Discovery/QUICK-START-DOCKER.md](Engines/Discovery/QUICK-START-DOCKER.md)** - Discovery quick start

## Next Steps

1. ✅ Start Docker Desktop
2. ✅ Run: `run-complete-test.bat`
3. ✅ Watch devices being discovered
4. ✅ Experiment with different device counts
5. ✅ Test your own discovery implementations

Happy testing! 🚀
