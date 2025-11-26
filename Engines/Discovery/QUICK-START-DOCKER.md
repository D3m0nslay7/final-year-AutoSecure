# Discovery Engine + Test Devices - Quick Start

## Complete Setup in 3 Steps

### Step 1: Start Docker Desktop

Make sure Docker Desktop is running. Check with:
```batch
docker ps
```

### Step 2: Start Test Devices

```batch
cd Devices
run-all-devices.bat
```

This starts:
- 2x mDNS Generic IoT Devices
- 2x mDNS HomeKit Devices
- 2x SSDP Generic Devices
- 1x MQTT Mosquitto Broker
- 1x MQTT HiveMQ Broker
- 1x MQTT EMQX Broker

**Total: 9 devices** on the Docker bridge network

### Step 3: Run Discovery Engine

```batch
cd Engines\Discovery
run-discovery-engine.bat
```

The Discovery Engine will find all 9 devices! 🎉

## What Happens

```
Docker Bridge Network (172.17.0.0/16)
│
├─ 9 Test Device Containers (172.17.0.2-10)
│  ├─ mDNS devices broadcasting
│  ├─ SSDP devices responding
│  └─ MQTT brokers listening
│
└─ Discovery Engine Container (172.17.0.11)
   └─ Scans network → Finds all 9 devices!
```

## Output Example

```
============================================================
Starting Device Discovery Engine
============================================================

[1/4] Running mDNS Discovery...
  ✓ Found: GenericIoTDevice-1234
  ✓ Found: SmartLight-5678
  Found 2 mDNS device(s)

[2/4] Running SSDP Discovery...
  ✓ Found: upnp:rootdevice at 172.17.0.5
  Found 2 SSDP device(s)

[3/4] Running MQTT Discovery...
  ✓ Found: Mosquitto at 172.17.0.8:1883
  ✓ Found: HiveMQ at 172.17.0.9:8883
  ✓ Found: EMQX at 172.17.0.10:8884

[Enrichment] Using ARP to get MAC addresses...

============================================================
Discovery Complete - Total Devices: 9
============================================================
```

Each device shows:
- ✅ Unique IP address
- ✅ Unique MAC address
- ✅ Device type and protocol
- ✅ Port and properties
- ✅ Discovery method used

## Customize

### Run More Devices

```batch
cd Devices\mDNS
run-generic.bat 10    # 10 Generic IoT devices

cd ..\SSDP
run-generic.bat 20    # 20 SSDP devices
```

Then run discovery again - it will find all of them!

### Longer Scan Duration

```batch
cd Engines\Discovery
run-discovery-custom.bat 30    # 30-second scan
```

## Stop Everything

```batch
cd Devices
stop-all-devices.bat
```

## Troubleshooting

**No devices found?**
1. Check devices are running: `docker ps --filter name=autosecure-`
2. Try longer scan: `run-discovery-custom.bat 30`

**Permission errors?**
- The run script includes required permissions automatically

**Need help?**
- See [DOCKER-README.md](DOCKER-README.md) for detailed documentation

---

That's it! You now have a complete Docker-based IoT discovery testing environment! 🚀
