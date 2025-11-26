# Quick Start Guide

## 1. Run All Devices (Recommended for First Time)

```batch
run-all-devices.bat
```

This will start:
- ✅ 2 mDNS Generic IoT Devices
- ✅ 2 mDNS HomeKit Devices
- ✅ 2 SSDP Generic Devices
- ✅ 1 MQTT Mosquitto Broker
- ✅ 1 MQTT HiveMQ Broker
- ✅ 1 MQTT EMQX Broker

**Total: 9 devices** ready for discovery testing!

## 2. Verify Devices Are Running

```batch
list-devices.bat
```

You should see all containers running with their unique IPs.

## 3. Run Your Discovery Engine

Point your Discovery Engine to scan the Docker network:
```
Network: 172.17.0.0/16
```

Each container has its own:
- ✅ Unique IP address (e.g., 172.17.0.2, 172.17.0.3, ...)
- ✅ Unique MAC address
- ✅ Unique device ID

## 4. Run Multiple Instances of a Device

Want to test with 5 Generic IoT devices?

```batch
cd mDNS
run-generic.bat 5
```

This creates 5 separate containers:
- `autosecure-mdns-generic-1` (IP: 172.17.0.2)
- `autosecure-mdns-generic-2` (IP: 172.17.0.3)
- `autosecure-mdns-generic-3` (IP: 172.17.0.4)
- `autosecure-mdns-generic-4` (IP: 172.17.0.5)
- `autosecure-mdns-generic-5` (IP: 172.17.0.6)

Each appears as a **completely separate device** to your Discovery Engine!

## 5. Stop All Devices

```batch
stop-all-devices.bat
```

## Common Commands

### Run Specific Device Types

```batch
# 10 Generic IoT devices
cd mDNS
run-generic.bat 10

# 5 HomeKit devices
cd mDNS
run-homekit.bat 5

# 20 SSDP devices
cd SSDP
run-generic.bat 20

# 3 Mosquitto brokers
cd MQTT
run-mosquitto.bat 3
```

### View Logs

```batch
# View logs for a specific device
docker logs autosecure-mdns-generic-1

# Follow logs in real-time
docker logs -f autosecure-mqtt-mosquitto-1
```

### Check Container Details

```batch
# Get IP address
docker inspect autosecure-mdns-generic-1 | findstr IPAddress

# Get MAC address
docker inspect autosecure-mdns-generic-1 | findstr MacAddress
```

## Example Testing Scenarios

### Scenario 1: Basic Discovery Test
```batch
run-all-devices.bat
# Run your Discovery Engine
# It should find 9 devices
```

### Scenario 2: Stress Test with 50 Devices
```batch
cd mDNS
run-generic.bat 20

cd ..\SSDP
run-generic.bat 20

cd ..\MQTT
run-mosquitto.bat 10

# Total: 50 devices
```

### Scenario 3: Specific Protocol Testing
```batch
# Test only MQTT discovery
cd MQTT
run-mosquitto.bat 5
run-hivemq.bat 3
run-emqx.bat 2

# Total: 10 MQTT brokers with unique IPs
```

## Key Points

✅ **Each container = separate device** with unique IP/MAC
✅ **Run scripts support multiple instances**: `run-generic.bat 5`
✅ **All devices are on Docker bridge network**: `172.17.0.0/16`
✅ **Easy cleanup**: `stop-all-devices.bat`

## Need Help?

See [README.md](README.md) for detailed documentation.
