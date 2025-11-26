# AutoSecure Test Devices - Docker Setup

Run IoT test devices in isolated Docker containers with unique IPs and MAC addresses for realistic network discovery testing.

## Quick Start

### Run All Devices (Default Configuration)
```batch
run-all-devices.bat
```

This starts:
- 2x mDNS Generic IoT Devices
- 2x mDNS HomeKit Devices
- 2x SSDP Generic Devices
- 1x MQTT Mosquitto Broker
- 1x MQTT HiveMQ Broker
- 1x MQTT EMQX Broker

### Run Specific Device Types

Navigate to the device folder and run the script:

```batch
# mDNS devices
cd mDNS
run-generic.bat 5      # Run 5 Generic IoT devices
run-homekit.bat 3      # Run 3 HomeKit devices

# SSDP devices
cd SSDP
run-generic.bat 10     # Run 10 SSDP devices

# MQTT brokers
cd MQTT
run-mosquitto.bat 2    # Run 2 Mosquitto brokers
run-hivemq.bat 1       # Run 1 HiveMQ broker
run-emqx.bat 1         # Run 1 EMQX broker
```

### Stop All Devices
```batch
stop-all-devices.bat
```

### List Running Devices
```batch
list-devices.bat
```

## Features

### Multiple Instances
Each device script accepts a number argument to spawn multiple instances:
```batch
cd mDNS
run-generic.bat 5      # Spawns 5 separate containers
```

Each instance gets:
- **Unique container name** (`autosecure-mdns-generic-1`, `autosecure-mdns-generic-2`, etc.)
- **Unique IP address** (Docker assigns each container its own IP)
- **Unique MAC address** (Docker assigns each container its own MAC)
- **Unique device ID** (randomly generated for each instance)

### Separate Containers = Separate Network Devices
Each container runs on Docker's bridge network, giving it:
- Its own IP address
- Its own MAC address
- Its own network interface

This means your Discovery Engine will see them as **completely separate devices** on the network, just like real IoT devices!

## Project Structure

```
Devices/
├── mDNS/
│   ├── Dockerfile                  # mDNS container image
│   ├── generic_iot_device.py       # Generic IoT device
│   ├── homekit_device.py           # HomeKit device
│   ├── run-generic.bat             # Run Generic IoT (supports multiple instances)
│   └── run-homekit.bat             # Run HomeKit (supports multiple instances)
│
├── SSDP/
│   ├── Dockerfile                  # SSDP container image
│   ├── generic_ssdp_device.py      # SSDP device
│   └── run-generic.bat             # Run SSDP (supports multiple instances)
│
├── MQTT/
│   ├── Dockerfile                  # MQTT container image
│   ├── mosquitto_broker.py         # Mosquitto broker
│   ├── hivemq_broker.py            # HiveMQ broker
│   ├── emqx_broker.py              # EMQX broker
│   ├── run-mosquitto.bat           # Run Mosquitto (supports multiple instances)
│   ├── run-hivemq.bat              # Run HiveMQ (supports multiple instances)
│   └── run-emqx.bat                # Run EMQX (supports multiple instances)
│
├── run-all-devices.bat             # Master script to start all devices
├── stop-all-devices.bat            # Stop all AutoSecure containers
├── list-devices.bat                # List running containers
├── docker-compose.yml              # Docker Compose config (single instances)
└── README.md                       # This file
```

## Device Types

### mDNS Devices
- **Generic IoT Device** - Broadcasts `_http._tcp.local.` service
- **HomeKit Device** - Broadcasts `_hap._tcp.local.` service (smart light bulb)

### SSDP Devices
- **Generic SSDP** - Broadcasts UPnP device (MediaRenderer, MediaServer, or Basic)

### MQTT Brokers
- **Mosquitto** - MQTT 3.1.1 on port 1883
- **HiveMQ** - MQTT 5.0 on port 8883 + Web UI on port 8000
- **EMQX** - MQTT 5.0 on port 8884 + Dashboard on port 18083

## How It Works

### Container Networking
Each container runs in Docker's default `bridge` network:
```
Host Machine (Your PC)
├── autosecure-mdns-generic-1 (IP: 172.17.0.2, MAC: 02:42:ac:11:00:02)
├── autosecure-mdns-generic-2 (IP: 172.17.0.3, MAC: 02:42:ac:11:00:03)
├── autosecure-mdns-generic-3 (IP: 172.17.0.4, MAC: 02:42:ac:11:00:04)
└── autosecure-mqtt-mosquitto-1 (IP: 172.17.0.5, MAC: 02:42:ac:11:00:05)
```

Your Discovery Engine can scan the `172.17.0.0/16` network to find all devices.

### Dynamic Device IDs
Each device instance gets a unique ID via environment variables:
```python
device_id = os.getenv('DEVICE_ID', str(random.randint(1000, 9999)))
```

The run scripts pass a random ID to each container:
```batch
docker run -e DEVICE_ID=%RANDOM%%RANDOM% ...
```

## Usage Examples

### Scenario 1: Test Discovery with 10 Devices
```batch
cd mDNS
run-generic.bat 10

# Your Discovery Engine should find 10 separate mDNS devices
```

### Scenario 2: Mix of Different Device Types
```batch
cd mDNS
run-generic.bat 3
run-homekit.bat 2

cd ..\SSDP
run-generic.bat 5

cd ..\MQTT
run-mosquitto.bat 1

# Total: 11 devices on the network
```

### Scenario 3: Stress Test with 50 Devices
```batch
cd mDNS
run-generic.bat 20
run-homekit.bat 10

cd ..\SSDP
run-generic.bat 20

# 50 total devices for stress testing
```

## Managing Containers

### View Logs
```batch
# View logs for specific container
docker logs autosecure-mdns-generic-1

# Follow logs in real-time
docker logs -f autosecure-mqtt-mosquitto-1

# View last 50 lines
docker logs --tail 50 autosecure-ssdp-generic-1
```

### Stop Specific Containers
```batch
# Stop single container
docker stop autosecure-mdns-generic-1

# Stop all Generic IoT devices
docker stop $(docker ps -q --filter name=autosecure-mdns-generic)

# Stop all mDNS devices
docker stop $(docker ps -q --filter name=autosecure-mdns)
```

### Remove Specific Containers
```batch
# Remove single container
docker rm autosecure-mdns-generic-1

# Remove all stopped AutoSecure containers
docker container prune --filter label=autosecure
```

### Inspect Container Network
```batch
# Get container IP address
docker inspect autosecure-mdns-generic-1 | findstr IPAddress

# Get container MAC address
docker inspect autosecure-mdns-generic-1 | findstr MacAddress

# View all network details
docker inspect autosecure-mdns-generic-1
```

## Port Mappings

MQTT brokers expose ports to the host:

| Broker | Container Port | Host Port(s) | Description |
|--------|---------------|--------------|-------------|
| Mosquitto | 1883 | 1883+ | MQTT (increments for multiple instances) |
| HiveMQ | 8883, 8000 | 8883+, 8000+ | MQTT + Web UI |
| EMQX | 8884, 18083 | 8884+, 18083+ | MQTT + Dashboard |

mDNS and SSDP devices don't expose ports as they use multicast protocols.

## Troubleshooting

### Port Already in Use
If you get port conflicts when running multiple MQTT brokers:
```
Error: Bind for 0.0.0.0:1883 failed: port is already allocated
```

The scripts automatically increment ports for multiple instances.

### Container Name Already Exists
```batch
# Remove existing container first
docker rm autosecure-mdns-generic-1

# Or stop and remove
docker stop autosecure-mdns-generic-1 && docker rm autosecure-mdns-generic-1
```

### Can't Find Devices from Discovery Engine
Make sure your Discovery Engine scans the Docker bridge network:
```python
# Scan Docker's default bridge network
network = "172.17.0.0/16"
```

Check container IPs:
```batch
docker inspect $(docker ps -q --filter name=autosecure) | findstr IPAddress
```

### Rebuild Containers After Code Changes
```batch
cd mDNS
docker build -t autosecure-mdns-generic . --no-cache
```

## Docker Compose (Alternative)

For simple single-instance deployment, use Docker Compose:

```batch
# Start all devices (1 of each)
docker-compose up -d

# Stop all devices
docker-compose down

# View logs
docker-compose logs -f
```

**Note:** Docker Compose doesn't support the multi-instance feature. Use the batch scripts for multiple instances.

## Advanced Usage

### Custom Environment Variables
```batch
# Custom device ID
docker run -e DEVICE_ID=MyDevice123 autosecure-mdns-generic

# Custom IP (for mDNS advertising, not actual container IP)
docker run -e DEVICE_IP=192.168.1.100 autosecure-mdns-generic

# Custom port
docker run -e DEVICE_PORT=8080 autosecure-mdns-generic
```

### Run in Interactive Mode
```batch
# See real-time output
docker run -it --rm --name test-device autosecure-mdns-generic
```

### Execute Commands in Running Container
```batch
# Get a shell inside the container
docker exec -it autosecure-mdns-generic-1 /bin/bash

# Run Python command
docker exec autosecure-mdns-generic-1 python -c "print('Hello')"
```

## Dependencies

The devices use these Python packages:
- **mDNS devices**: `zeroconf`
- **SSDP devices**: `ssdpy`
- **MQTT brokers**: No external dependencies (uses Python standard library)

All dependencies are installed automatically in the Docker images.

## Tips

1. **Start small**: Test with 1-2 devices first, then scale up
2. **Monitor resources**: Each container uses memory/CPU
3. **Clean up regularly**: Use `stop-all-devices.bat` to avoid container buildup
4. **Check logs**: If a device isn't being discovered, check its logs
5. **Network scanning**: Scan `172.17.0.0/16` to find all Docker containers

## Next Steps

1. Run devices: `run-all-devices.bat`
2. Start your Discovery Engine
3. Scan the Docker network (`172.17.0.0/16`)
4. Verify devices are discovered
5. Scale up for stress testing
