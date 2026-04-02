# AutoSecure

AutoSecure is an automated IoT network security system that discovers devices on a network, segments them by risk level, and monitors live traffic for attacks. It is designed and tested against Docker-simulated IoT environments.

---

## System Overview

AutoSecure operates as a three-phase pipeline coordinated by a central orchestrator:

```
┌──────────────────────────────────────────────────────────────┐
│  1. DISCOVERY   →   2. SEGMENTATION   →   3. MONITORING      │
│                                                              │
│  Scan network        Classify devices        Detect attacks  │
│  via protocols       Apply iptables rules    Parse tcpdump   │
│  Return registry     Isolate by segment      Raise alerts    │
└──────────────────────────────────────────────────────────────┘
```

**Entry point:** `Engines/main.py`

---

## Engines

### Discovery Engine — `Engines/Discovery/`

Discovers IoT devices on the network using four parallel protocol methods.

**File structure:**
```
Discovery/
├── discovery_engine.py
├── modules/
│   ├── core/
│   │   ├── network_scanner.py
│   │   └── port_scanner.py
│   └── protocols/
│       ├── mdns_module.py
│       ├── ssdp_module.py
│       ├── arp_module.py
│       └── mqtt_detector.py
├── requirements.txt
└── Dockerfile
```

**How it works:**

The `DiscoveryEngine` class runs all four protocol modules and merges results into a single device registry, deduplicating by IP address.

| Module | Protocol | What it finds |
|--------|----------|--------------|
| `mdns_module.py` | mDNS / Zeroconf | HomeKit, generic IoT (`_http._tcp.local.`, `_hap._tcp.local.`) |
| `ssdp_module.py` | SSDP / UPnP | UPnP devices (media renderers, servers, basic devices) |
| `mqtt_detector.py` | MQTT | Mosquitto, HiveMQ, EMQX brokers |
| `arp_module.py` | ARP | Any IP-reachable device; enriches all results with MAC addresses |

**Discovery flow:**
1. Run mDNS scan (10s) and SSDP scan (10s) in parallel
2. Run MQTT detector — port scans for 1883/8883/8884, verifies protocol, identifies vendor via web interface
3. Enrich all discovered IPs with MAC addresses via ARP
4. Filter out gateway devices (`.1` addresses)
5. Return merged device registry as a list of dicts with `ip`, `mac`, `hostname`, `type`, `source`

**Key dependencies:** `zeroconf`, `ssdpy`, `scapy`, `paho-mqtt`, `requests`

---

### Segmentation Engine — `Engines/Segmentation/`

Classifies discovered devices into security segments and enforces isolation via iptables.

**File structure:**
```
Segmentation/
├── segmentation_engine.py
├── segment_config.py
└── iptables_manager.py
```

**Segments:**

| Segment | Assigned to | Allowed traffic |
|---------|-------------|----------------|
| `iot` | mDNS / SSDP / MQTT devices | Internet on ports 80, 443, 8883 only. Blocked from internal network. |
| `trusted` | Manually designated devices | Full internal + internet access |
| `quarantine` | Unknown / unrecognised devices | Completely isolated — no internal, no external |

**How it works:**

1. `SegmentationEngine` receives the device registry from Discovery
2. Each device is classified based on its `source` field (mDNS → iot, unknown → quarantine)
3. `IptablesManager` creates three custom iptables chains: `AUTOSECURE_IOT`, `AUTOSECURE_TRUSTED`, `AUTOSECURE_QUARANTINE`
4. Rules are applied per-device IP into the appropriate chain
5. Active rules are printed to stdout after application

---

### Monitoring Engine — `Engines/Monitoring/`

Monitors live network traffic inside Docker containers for attacks and policy violations.

**File structure:**
```
Monitoring/
├── monitoring_engine.py
└── __init__.py
```

**How it works:**

The `MonitoringEngine` class uses `docker exec tcpdump` to capture traffic inside each discovered device container rather than passive host-level sniffing. A separate thread is spawned per container, and tcpdump output is parsed in real-time with regex.

**Detections:**

| Alert Type | Trigger |
|------------|---------|
| `ARP_SPOOF` | An IP claims a MAC address different from its previously seen MAC |
| `UNENCRYPTED_MQTT` | Plain MQTT traffic detected on port 1883 (should use 8883 with TLS) |
| `POLICY_VIOLATION` | Traffic detected between devices that should be in isolated segments |
| `PORT_SCAN` | A single source probes more than 10 distinct ports within 10 seconds |

**Alert behaviour:**
- Alerts are deduplicated per source — the same alert from the same source is only raised once
- All alerts are thread-safe via a shared lock
- A summary report is printed at the end of the monitoring window (default: 60 seconds)

---

### Main Orchestrator — `Engines/main.py`

Ties all three engines together in sequence:

```python
1. discovery  = DiscoveryEngine()
2. devices    = discovery.discover_all()
3. segmenter  = SegmentationEngine(devices)
4. segmenter.apply_segmentation()
5. # Print iptables rules
6. monitor    = MonitoringEngine(devices)
7. monitor.start(duration=60)
```

---

## Test Infrastructure

### Simulated Devices — `Devices/`

Docker containers that emulate real IoT device behaviour for testing discovery and monitoring:

| Folder | Device type | Protocol |
|--------|-------------|----------|
| `Devices/mDNS/` | Generic IoT, HomeKit Smart Light | mDNS |
| `Devices/SSDP/` | UPnP MediaRenderer, MediaServer, Basic | SSDP |
| `Devices/MQTT/mosquitto/` | Mosquitto broker | MQTT 3.1.1 on port 1883 |
| `Devices/MQTT/hivemq/` | HiveMQ broker | MQTT 5.0 on port 8883, Web UI on 8000 |
| `Devices/MQTT/emqx/` | EMQX broker | MQTT 5.0 on port 8884, Dashboard on 18083 |

All containers run on the Docker bridge network (`172.17.0.0/16`) with unique IPs and MAC addresses.

### Attack Scripts — `Attacks/`

Simulation scripts for testing that the Monitoring Engine raises correct alerts:

| Script | Simulates |
|--------|-----------|
| `attack_arp_spoof.py` | ARP spoofing / man-in-the-middle |
| `attack_mosquitto.py` | Attacks against Mosquitto broker |
| `attack_hivemq.py` | Attacks against HiveMQ broker |
| `attack_emqx.py` | Attacks against EMQX broker |
| `attack_homekit.py` | Attacks against HomeKit devices |
| `attack_ssdp.py` | SSDP-based attacks |
| `attack_generic_iot.py` | Generic IoT device attacks |
| `get_docker_ips.py` | Utility — prints container IPs |

---

## Running the System

See [DOCKER-SETUP.md](DOCKER-SETUP.md) for full environment setup.

**Quick start:**
```bash
# Start all simulated device containers
# (see DOCKER-SETUP.md)

# Run the full pipeline
python Engines/main.py

# Run with attack simulation
run-attack-test.bat
```

**Requirements:** Python 3.x, Docker, Linux (iptables), root/admin privileges for ARP scanning and iptables
