"""
log_generator.py — OT Log & Telemetry Generator
Generates realistic OT logs, events, and network telemetry
for consumption by Logstash/Elasticsearch.
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import json
import logging
import random
import socket
import struct
import time
import threading
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [logger] %(levelname)s: %(message)s",
)
log = logging.getLogger("log_generator")

CONFIG = {
    "elasticsearch_url": "http://elasticsearch:9200",
    "logstash_tcp_host": "logstash",
    "logstash_tcp_port": 5000,
    "index_prefix": "ot-lab",
    "node_name": socket.gethostname(),
    "interval": 3,
}


def generate_modbus_log():
    """Generate a Modbus protocol event log."""
    return {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "event": {
            "kind": "event",
            "category": "network",
            "type": ["connection", "protocol"],
            "action": random.choice(["read_coil", "read_register", "write_register", "write_coil"]),
        },
        "network": {
            "protocol": "modbus",
            "transport": "tcp",
            "port": 5020,
        },
        "modbus": {
            "function_code": random.choice([1, 2, 3, 4, 5, 6, 15, 16]),
            "unit_id": random.randint(1, 10),
            "register_address": random.randint(0, 100),
            "register_value": random.randint(0, 65535),
            "transaction_id": random.randint(1000, 99999),
        },
        "source": {
            "ip": f"172.30.{random.randint(0, 5)}.{random.randint(2, 254)}",
            "port": random.randint(40000, 60000),
        },
        "destination": {
            "ip": "172.30.1.100",
            "port": 5020,
        },
        "observer": {
            "name": CONFIG["node_name"],
            "type": "sensor",
        },
        "tags": ["ot-lab", "modbus"],
    }


def generate_bacnet_log():
    """Generate a BACnet protocol event log."""
    return {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "event": {
            "kind": "event",
            "category": "network",
            "type": ["connection", "protocol"],
            "action": random.choice(["read_property", "write_property", "who_is", "i_am"]),
        },
        "network": {
            "protocol": "bacnet",
            "transport": "udp",
            "port": 47808,
        },
        "bacnet": {
            "device_id": random.choice([1001, 1002, 2001]),
            "object_type": random.choice(["analogInput", "analogOutput", "binaryInput", "binaryOutput"]),
            "object_instance": random.randint(0, 10),
            "property": random.choice(["presentValue", "statusFlags", "outOfService"]),
            "value": round(random.uniform(0, 100), 2),
        },
        "source": {
            "ip": f"172.30.{random.randint(0, 3)}.{random.randint(2, 254)}",
        },
        "observer": {"name": CONFIG["node_name"]},
        "tags": ["ot-lab", "bacnet"],
    }


def generate_mqtt_log():
    """Generate an MQTT event log."""
    topics = [
        "ot/plant1/reactor/temperature",
        "ot/plant1/reactor/pressure",
        "ot/plant1/piping/flow_rate",
        "ot/plant1/cmd/pump/start",
        "ot/plant1/alarm/high_temperature",
        "ot/plant1/status/system",
    ]
    return {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "event": {
            "kind": "event",
            "category": "network",
            "type": ["protocol"],
            "action": random.choice(["publish", "subscribe", "connect"]),
        },
        "network": {"protocol": "mqtt", "transport": "tcp", "port": 1883},
        "mqtt": {
            "topic": random.choice(topics),
            "qos": random.choice([0, 1, 2]),
            "packet_size": random.randint(20, 500),
            "retain": random.choice([True, False]),
        },
        "source": {
            "ip": f"172.30.{random.randint(0, 5)}.{random.randint(2, 254)}",
            "port": random.randint(30000, 50000),
        },
        "observer": {"name": CONFIG["node_name"]},
        "tags": ["ot-lab", "mqtt"],
    }


def generate_opcua_log():
    """Generate an OPC UA event log."""
    return {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "event": {
            "kind": "event",
            "category": "network",
            "type": ["protocol"],
            "action": random.choice(["browse", "read", "write", "subscribe"]),
        },
        "network": {"protocol": "opcua", "transport": "tcp", "port": 4840},
        "opcua": {
            "node_id": f"ns=1;s={random.choice(['Temperature', 'Pressure', 'FlowRate', 'ValvePosition'])}",
            "value": round(random.uniform(0, 1000), 2),
            "security_mode": random.choice(["None", "Basic256Sha256"]),
        },
        "source": {
            "ip": f"172.30.{random.randint(0, 5)}.{random.randint(2, 254)}",
        },
        "observer": {"name": CONFIG["node_name"]},
        "tags": ["ot-lab", "opcua"],
    }


def generate_s7_log():
    """Generate an S7 event log."""
    return {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "event": {
            "kind": "event",
            "category": "network",
            "type": ["protocol"],
            "action": random.choice(["read_db", "write_db", "connection", "setup"]),
        },
        "network": {"protocol": "s7", "transport": "tcp", "port": 102},
        "s7": {
            "data_block": random.randint(1, 5),
            "function": random.choice(["READ", "WRITE", "REQ", "RESP"]),
            "rack": 0,
            "slot": random.choice([1, 2, 3]),
        },
        "source": {"ip": f"172.30.{random.randint(0, 5)}.{random.randint(2, 254)}"},
        "observer": {"name": CONFIG["node_name"]},
        "tags": ["ot-lab", "s7"],
    }


def generate_enip_log():
    """Generate an Ethernet/IP event log."""
    return {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "event": {
            "kind": "event",
            "category": "network",
            "type": ["protocol"],
            "action": random.choice(["register_session", "read_tag", "write_tag", "list_identity"]),
        },
        "network": {"protocol": "enip", "transport": "tcp", "port": 44818},
        "enip": {
            "command": random.choice([0x0065, 0x0072, 0x0001]),
            "tag": random.choice(["Temperature_PV", "Pressure_PV", "Valve_Cmd", "Pump_Speed"]),
        },
        "source": {"ip": f"172.30.{random.randint(0, 5)}.{random.randint(2, 254)}"},
        "observer": {"name": CONFIG["node_name"]},
        "tags": ["ot-lab", "enip"],
    }


def generate_security_log():
    """Generate security-relevant events (attacks/anomalies)."""
    event_types = [
        {"action": "unauthorized_write", "severity": "high"},
        {"action": "connection_scan", "severity": "medium"},
        {"action": "protocol_anomaly", "severity": "high"},
        {"action": "authentication_failure", "severity": "medium"},
        {"action": "alarm_triggered", "severity": "critical"},
        {"action": "value_out_of_range", "severity": "high"},
        {"action": "configuration_change", "severity": "info"},
        {"action": "firmware_version_mismatch", "severity": "medium"},
    ]
    ev = random.choice(event_types)
    return {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "event": {
            "kind": "alert",
            "category": "intrusion_detection",
            "type": ["indicator"],
            "action": ev["action"],
            "severity": ev["severity"],
        },
        "network": {
            "protocol": random.choice(["modbus", "bacnet", "mqtt", "opcua", "s7", "enip"]),
        },
        "threat": {
            "indicator": f"172.30.{random.randint(0, 5)}.{random.randint(2, 254)}",
            "type": random.choice(["ip", "behavioral"]),
            "confidence": random.choice(["low", "medium", "high"]),
        },
        "source": {"ip": f"172.30.{random.randint(0, 5)}.{random.randint(2, 254)}"},
        "message": random.choice([
            "Write to critical register outside normal range",
            "Rapid connection attempts detected from single source",
            "Invalid protocol frame structure detected",
            "Repeated authentication failures on SCADA endpoint",
            "Process value exceeded alarm threshold",
            "Configuration modification via unauthorized source",
        ]),
        "observer": {"name": CONFIG["node_name"]},
        "tags": ["ot-lab", "security", ev["severity"]],
    }


def generate_process_log():
    """Generate process/SCADA events."""
    return {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "event": {
            "kind": "event",
            "category": "process",
            "type": ["info"],
            "action": random.choice([
                "temperature_update", "pressure_update", "flow_update",
                "level_change", "valve_adjust", "pump_start", "pump_stop",
            ]),
        },
        "process": {
            "value": round(random.uniform(0, 1000), 2),
            "unit": random.choice(["°C", "bar", "L/min", "%", "RPM", "kW"]),
            "quality": random.choice(["good", "good", "good", "uncertain", "bad"]),
        },
        "observer": {"name": CONFIG["node_name"]},
        "tags": ["ot-lab", "process"],
    }


LOG_GENERATORS = [
    generate_modbus_log,
    generate_bacnet_log,
    generate_mqtt_log,
    generate_opcua_log,
    generate_s7_log,
    generate_enip_log,
    generate_security_log,
    generate_process_log,
]


def send_to_elasticsearch(doc):
    """Send log document to Elasticsearch via HTTP API."""
    try:
        index = f"{CONFIG['index_prefix']}-{time.strftime('%Y.%m.%d')}"
        url = f"{CONFIG['elasticsearch_url']}/{index}/_doc"
        resp = requests.post(url, json=doc, timeout=2)
        if resp.status_code not in (200, 201):
            log.warning(f"ES write failed: {resp.status_code}")
    except requests.RequestException as e:
        log.debug(f"ES write error: {e}")


def send_to_logstash(doc):
    """Send log document to Logstash via TCP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((CONFIG["logstash_tcp_host"], CONFIG["logstash_tcp_port"]))
        data = (json.dumps(doc) + "\n").encode()
        sock.send(data)
        sock.close()
    except Exception as e:
        log.debug(f"Logstash send error: {e}")


def write_to_stdout(doc):
    """Write log as JSON to stdout (for Docker logging)."""
    print(json.dumps(doc))
    log.debug(f"Generated: {doc.get('event', {}).get('action', 'unknown')}")


def main():
    log.info("OT Log Generator Starting")

    # Burst of initial logs to populate ES
    log.info("Generating initial log burst...")
    for _ in range(50):
        gen = random.choice(LOG_GENERATORS)
        doc = gen()
        send_to_elasticsearch(doc)
        write_to_stdout(doc)
        time.sleep(0.05)

    log.info(f"Sending logs every {CONFIG['interval']}s")

    while True:
        try:
            gen = random.choice(LOG_GENERATORS)
            doc = gen()

            # Send to all outputs
            send_to_elasticsearch(doc)
            send_to_logstash(doc)
            write_to_stdout(doc)

            # Occasionally send bursts
            if random.random() < 0.1:  # 10% chance of burst
                for _ in range(random.randint(3, 8)):
                    gen = random.choice(LOG_GENERATORS)
                    doc = gen()
                    send_to_elasticsearch(doc)
                    write_to_stdout(doc)
                    time.sleep(0.1)

            time.sleep(CONFIG["interval"])

        except Exception as e:
            log.error(f"Log generation error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
