"""
enip_sim.py — EtherNet/IP Simulator
Simulates an industrial Ethernet/IP device with tag-based data.
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import time
import random
import logging
import struct
import threading
import socket

log = logging.getLogger("enip_sim")

# Simulated tag database
TAGS = {
    "Temperature_PV": {"type": "REAL", "value": 235.0, "access": "readonly"},
    "Pressure_PV": {"type": "REAL", "value": 45.0, "access": "readonly"},
    "FlowRate_PV": {"type": "REAL", "value": 1200.0, "access": "readonly"},
    "TankLevel_PV": {"type": "REAL", "value": 78.0, "access": "readonly"},
    "Valve_Cmd": {"type": "REAL", "value": 75.0, "access": "readwrite"},
    "Pump_Speed": {"type": "DINT", "value": 1450, "access": "readwrite"},
    "System_Online": {"type": "BOOL", "value": True, "access": "readonly"},
    "Alarm_Active": {"type": "BOOL", "value": False, "access": "readonly"},
    "Pump_Running": {"type": "BOOL", "value": True, "access": "readonly"},
    "Motor_Current": {"type": "REAL", "value": 35.0, "access": "readonly"},
    "Power_Total": {"type": "REAL", "value": 450.0, "access": "readonly"},
    "Setpoint_Temp": {"type": "REAL", "value": 240.0, "access": "readwrite"},
}


def enip_register_session():
    """Build EtherNet/IP register session response."""
    return bytes([
        0x00, 0x00, 0x00, 0x00,  # Command: Register Session
        0x02, 0x00,  # Length
        0x00, 0x00,  # Session handle (placeholder)
        0x00, 0x00, 0x00, 0x00,  # Status
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Sender context
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Options
        0x01, 0x00,  # Protocol version
        0x00, 0x00,  # Options flags
    ])


def enip_send_rr_data(tag_name):
    """Build a send_rr_data response for a tag read."""
    tag = TAGS.get(tag_name)
    if not tag:
        return None

    value_bytes = bytearray()
    if tag["type"] == "REAL":
        value_bytes.extend(struct.pack('<f', tag["value"]))
    elif tag["type"] == "DINT":
        value_bytes.extend(struct.pack('<i', tag["value"]))
    elif tag["type"] == "BOOL":
        value_bytes.extend(struct.pack('<?', tag["value"]))
    elif tag["type"] == "INT":
        value_bytes.extend(struct.pack('<h', tag["value"]))

    return_code = 0x00  # Success
    item_data = bytes([return_code]) + bytes(value_bytes)
    item_len = len(item_data)

    # Build CIP response
    response = bytearray()
    response.extend(bytes([
        0x00, 0x00, 0x00, 0x00,  # Command: SendRRData
        0x00, 0x00,  # Length (placeholder)
        0x00, 0x00,  # Session
        0x00, 0x00, 0x00, 0x00,  # Status
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        # Interface handle
        0x00, 0x00, 0x00, 0x00,
        # Timeout
        0x00, 0x00, 0x00, 0x00,
        # Item count
        0x02, 0x00,
        # Item 0: Null address
        0x00, 0x00, 0x00, 0x00,
        # Item 1: Unconnected data
        0x00, 0x00,  # Type ID
    ]))

    data_len_pos = len(response)
    response.extend(struct.pack('<H', item_len))

    response.extend([
        0x00, 0x00, 0x00, 0x00,  # Reply service
    ])
    response.extend(item_data)

    total_len = len(response) - 24  # Subtract header
    response[4:6] = struct.pack('<H', total_len)

    return response


def handle_enip_client(conn, addr):
    """Handle an ENIP client connection."""
    log.info(f"ENIP connection from {addr}")
    session_handle = hash(addr) & 0xFFFF

    try:
        while True:
            data = conn.recv(65535)
            if not data:
                break

            if len(data) < 24:
                continue

            command = struct.unpack_from('<H', data, 0)[0]

            if command == 0x0001:  # List Identity
                conn.send(bytes([
                    0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                ]))

            elif command == 0x0065:  # Register Session
                resp = enip_register_session()
                resp[6:8] = struct.pack('<H', session_handle)
                conn.send(resp)
                log.info(f"ENIP session registered: {session_handle:04x}")

            elif command == 0x0072:  # SendRRData
                # Parse request to extract tag name
                req_data = data[44:] if len(data) > 44 else data[24:]
                tag_name = None
                for tname in TAGS:
                    if tname.encode() in req_data:
                        tag_name = tname
                        break

                if tag_name:
                    resp = enip_send_rr_data(tag_name)
                    if resp:
                        conn.send(resp)
                        log.debug(f"ENIP read {tag_name} = {TAGS[tag_name]['value']}")
                else:
                    log.debug(f"ENIP unknown tag request from {addr}")

            elif command == 0x0066:  # Unregister Session
                log.info(f"ENIP session {session_handle:04x} closed")
                break

    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        log.info(f"ENIP client {addr} disconnected: {e}")
    finally:
        conn.close()


def _update_tags():
    """Simulate process value changes."""
    for name, tag in TAGS.items():
        if tag["access"] == "readonly":
            if "Temperature" in name:
                tag["value"] = max(100, min(500, tag["value"] + random.gauss(0, 0.3)))
            elif "Pressure" in name:
                tag["value"] = max(0, min(80, tag["value"] + random.gauss(0, 0.2)))
            elif "FlowRate" in name:
                tag["value"] = max(0, min(2000, tag["value"] + random.gauss(0, 5)))
            elif "TankLevel" in name:
                tag["value"] = max(0, min(100, tag["value"] - 0.02 + random.gauss(0, 0.1)))
            elif "Motor" in name:
                tag["value"] = max(0, min(100, tag["value"] + random.gauss(0, 0.5)))
            elif "Power" in name:
                tag["value"] = max(0, min(1000, tag["value"] + random.gauss(0, 2)))


def run_enip_sim(host="0.0.0.0", port=44818):
    """Run the EtherNet/IP simulator."""
    # Process update thread
    def process_loop():
        while True:
            _update_tags()
            time.sleep(2)

    t = threading.Thread(target=process_loop, daemon=True)
    t.start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    server.settimeout(1.0)

    log.info(f"ENIP simulator listening on {host}:{port}")

    try:
        while True:
            try:
                conn, addr = server.accept()
                t = threading.Thread(
                    target=handle_enip_client, args=(conn, addr), daemon=True
                )
                t.start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
