# OT-ICS Security Education Lab

> **⚠ WARNING: FOR ISOLATED EDUCATIONAL USE ONLY — NEVER USE ON REAL SYSTEMS ⚠**

A Docker-based industrial control system (ICS) and operational technology (OT) security lab designed for education and training. Simulates a small industrial cyber range that runs fully isolated on a single laptop.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    OT-ICS Security Lab                   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Portal   │  │  Simulators   │  │  Attack Engine   │  │
│  │  :8080    │  │  :5020,4840,  │  │  (optional)      │  │
│  │  Web UI   │  │  47808,8102, │  │  :8081           │  │
│  │           │  │  44818,8082  │  │                  │  │
│  └─────┬─────┘  └──────┬───────┘  └────────┬─────────┘  │
│        │               │                    │            │
│  ┌─────┴───────────────┴────────────────────┴─────────┐  │
│  │              Log Collector + Logstash               │  │
│  └─────────────────────────┬──────────────────────────┘  │
│                            │                              │
│  ┌─────────────────────────┴──────────────────────────┐  │
│  │          Elasticsearch + Kibana (SIEM)              │  │
│  │                  :9200  :5601                       │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Safe Practice Area                      │  │
│  │              :9090, :5021, :4841                     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              MQTT Broker (Mosquitto)                 │  │
│  │              :1883                                  │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Components

| Service | Description | Port |
|---------|-------------|------|
| **Portal** | Central web dashboard for progress, quests, zones, achievements | 8080 |
| **Simulators** | Modbus, BACnet, OPC UA, MQTT, S7, Ethernet/IP, WebAPI | various |
| **Attack Engine** | Generates realistic OT attack scenarios (optional) | - |
| **Log Collector** | Generates OT logs and sends to Elasticsearch | - |
| **Elasticsearch** | SIEM search and analytics engine | 9200 |
| **Kibana** | SIEM visualization and dashboarding | 5601 |
| **Logstash** | Log ingestion and parsing | 5000 |
| **Safe Practice** | Isolated sandbox for protocol exploration | 9090 |
| **Mosquitto** | MQTT message broker | 1883 |

### Purdue Model Zones

| Level | Zone | Simulated Protocols |
|-------|------|-------------------|
| 0 | Physical Process | Sensors, actuators |
| 1 | Basic Control | Modbus, BACnet, S7, ENIP |
| 2 | Supervisory Control | OPC UA, SCADA WebAPI |
| 3 | Operations Management | MES, Historian |
| 4 | Enterprise Systems | ERP, Database |
| 5 | IT-OT DMZ | Firewall, Jump Box |

## Requirements

- Docker Engine 24.0+ 
- Docker Compose v2.20+
- 8 GB RAM minimum (16 GB recommended)
- 10 GB free disk space
- Modern laptop/desktop (x86_64 or ARM64)

## Quick Start

### 1. Clone and start

```bash
cd ot-security
docker compose up -d
```

### 2. First startup

On first run, the lab will:
1. Download Docker images (Elasticsearch, Kibana, Logstash, Mosquitto)
2. Build portal, simulators, and safe practice containers
3. Initialize the database with quests, zones, and achievements
4. Start generating OT telemetry and logs

Startup takes 2-5 minutes depending on your connection and hardware.

### 3. Access the lab

| Service | URL |
|---------|-----|
| **Web Portal** | http://localhost:8080 |
| **Kibana SIEM** | http://localhost:5601 |
| **Safe Practice** | http://localhost:9090 |

### 4. Enter the lab

Navigate to http://localhost:8080 and enter any username to begin.

## Optional: Enable Attack Scenarios

Attack scenarios are disabled by default. To enable them:

```bash
docker compose --profile attacks up -d attack-engine
```

The attack engine will run realistic OT attack scenarios at random intervals:
- Modbus register manipulation
- MQTT topic injection
- BACnet object manipulation
- SCADA API attacks
- Reconnaissance scanning
- Process anomaly injection
- S7 data block manipulation

## Usage

### Web Portal Features

- **Dashboard**: Overview of progress, zones, achievements, and services
- **Zones**: Explore the Purdue model levels and related quests
- **Quests**: Structured learning objectives for each protocol
- **Achievements**: Earn badges as you complete quests
- **Guides**: Protocol reference and detection methodology
- **Services**: Monitor and control lab components

### SIEM (Kibana)

1. Open http://localhost:5601
2. Go to **Discover** to search OT logs
3. Create dashboards to visualize protocol activity
4. Build correlations to detect attack patterns

Index pattern: `ot-lab-*`

### Safe Practice Area

The safe practice area (http://localhost:9090) provides an **isolated sandbox** where you can:
- Practice Modbus reads/writes on port 5021
- Explore OPC UA on port 4841
- Subscribe to MQTT topics on `practice/#`
- Run protocol fuzzing exercises
- Build custom process simulations

**This area is completely isolated from the main lab environment.**

## Simulated Protocols

| Protocol | Port | What it simulates |
|----------|------|------------------|
| Modbus TCP | 5020 | Temperature, pressure, flow, valve control |
| BACnet/IP | 47808 | HVAC controller with sensors and actuators |
| OPC UA | 4840 | Reactor cell, piping, power, safety systems |
| MQTT | 1883 | Plant telemetry, commands, alarms, status |
| S7 (Siemens) | 8102 | Data blocks with process values and setpoints |
| Ethernet/IP | 44818 | Tag-based data from industrial controller |
| WebAPI (SCADA) | 8082 | REST API for monitoring and control |

## Example Quests

### Beginner
- **Modbus Reconnaissance**: Scan and enumerate Modbus devices
- **BACnet Object Enumeration**: Discover building automation devices

### Intermediate
- **SCADA Traffic Analysis**: Capture and analyze industrial traffic
- **MQTT Protocol Exploitation**: Explore and detect MQTT attacks

### Advanced
- **Physical Process Anomaly Detection**: Identify attack-induced anomalies
- **IT-OT DMZ Monitoring**: Detect lateral movement
- **S7 Protocol Deep Dive**: Analyze Siemens PLC communication

## Lab Commands

```bash
# Start all services
docker compose up -d

# Start with attack engine
docker compose --profile attacks up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down

# Stop and remove volumes (reset lab)
docker compose down -v

# View running services
docker compose ps

# Restart a specific service
docker compose restart simulators
```

## Screenshots

*(Screenshots go here — see the portal at http://localhost:8080)*

> **Dashboard**: Shows quest progress, zone overview, achievements, and service status.
>
> **Quest Detail**: Step-by-step objectives with hints and completion tracking.
>
> **Kibana SIEM**: Log correlation and threat hunting dashboard.
>
> **Safe Practice**: Isolated exercise sandbox with guided tutorials.

## Educational Roadmap

### Week 1: Foundations
1. Access the portal and explore the dashboard
2. Complete "Modbus Reconnaissance" quest
3. Use tcpdump to capture Modbus traffic
4. View logs in Kibana

### Week 2: Protocol Analysis
1. Complete "BACnet Object Enumeration"
2. Complete "MQTT Protocol Exploitation"
3. Build a Kibana dashboard for protocol activity
4. Enable the attack engine and observe events

### Week 3: Detection
1. Complete "SCADA Traffic Analysis"
2. Complete "OPC UA Discovery & Security"
3. Identify attack patterns in Kibana
4. Practice in the Safe Practice Area

### Week 4: Advanced
1. Complete "Physical Process Anomaly Detection"
2. Complete "IT-OT DMZ Monitoring"
3. Build custom detection rules in Kibana
4. Chain multiple events to reconstruct attack scenarios

## ⚠ Legal and Ethical Notice

This software is provided **SOLELY for educational and authorized training purposes**.

**By using this software you agree that:**

1. You will **ONLY** use this lab in an isolated environment on systems you own
2. You will **NEVER** use techniques learned here against real systems without explicit written permission
3. You will **NOT** connect this lab to any network with real devices
4. You understand that real OT systems can cause **physical harm, environmental damage, or loss of life** if compromised
5. You accept **full responsibility** for any misuse of this software

### Safe Harbor

This lab is designed as a **defensive training tool**. The attack scenarios are simplified and intentionally detectable. Real OT attacks are more sophisticated and dangerous. Always practice responsible disclosure and ethical security research.

## Troubleshooting

### Elasticsearch fails to start
```bash
# Increase vm.max_map_count on Linux
sudo sysctl -w vm.max_map_count=262144
```

### Port conflicts
Edit `.env` to change port mappings:
```
PORTAL_PORT=8080
KIBANA_PORT=5601
```

### Attack engine not running
Verify it was started with the attacks profile:
```bash
docker compose --profile attacks up -d attack-engine
```

### Container logs
```bash
docker compose logs <service-name>
docker compose logs simulators
docker compose logs attack-engine
```

## License

Educational use only. See LICENSE file for terms.

---

**Built for OT security professionals, ICS defenders, and cybersecurity students.**
**Practice safely. Think critically. Protect critical infrastructure.**
