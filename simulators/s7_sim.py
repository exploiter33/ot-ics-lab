"""
s7_sim.py — Siemens S7 Protocol Simulator
Simulates S7 PLC communication with data blocks.
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import time
import struct
import random
import logging
import threading
import socket

log = logging.getLogger("s7_sim")

S7_PDU_SIZE = 256


def s7_cotp_cr():
    """Build S7 COTP connection request packet."""
    return bytes([
        0x03, 0x00, 0x00, 0x16,  # TPKT header (len=22)
        0x11, 0xE0, 0x00, 0x00, 0x00, 0x01,  # COTP connect request
        0x00, 0xC0, 0x01, 0x0A, 0xC0, 0x01, 0x0A, 0xC2, 0x02, 0x03, 0x00,
        0xC1, 0x02, 0x01, 0x00,
    ])


def s7_cotp_cc():
    """Build S7 COTP connection confirm."""
    return bytes([
        0x03, 0x00, 0x00, 0x16,
        0x11, 0xD0, 0x00, 0x00, 0x00, 0x01,
        0x00, 0xC0, 0x01, 0x0A, 0xC0, 0x01, 0x0A, 0xC2, 0x02, 0x03, 0x00,
        0xC1, 0x02, 0x01, 0x00,
    ])


def s7_setup_comm():
    """Build S7 setup communication response."""
    return bytes([
        0x03, 0x00, 0x00, 0x1A,
        0x02, 0xF0, 0x80,
        0x32, 0x01, 0x00, 0x00, 0x04, 0x00, 0x00, 0x08,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00,
    ])


def s7_read_response(data, db_values):
    """Build S7 read response for a DB read request."""
    if len(data) < 22:
        return None

    req_data = data[22:] if len(data) > 22 else data
    if len(req_data) < 2:
        return None

    function = req_data[0]
    if function != 0x04:  # Read
        return None

    param_len = req_data[1]
    item_count = req_data[2] if len(req_data) > 2 else 0
    if item_count < 1 or len(req_data) < 4 + 10:
        return None

    # Parse first item
    item_data = req_data[4:4 + 10]
    if len(item_data) < 10:
        return None

    var_type = item_data[2]
    db_num = (item_data[4] << 8) | item_data[5]
    area = item_data[3]
    start_addr = (item_data[6] << 8) | item_data[7]
    word_count = (item_data[8] << 8) | item_data[9]

    if area != 0x84:  # DB area
        return None

    # Build response data
    values = db_values.get(db_num, {})
    resp_data = bytearray()
    resp_data.append(0x00)  # Return code
    for i in range(word_count):
        addr = start_addr + i
        val = values.get(addr, 0)
        resp_data.extend(struct.pack('>H', val))

    total_len = 18 + len(resp_data)
    response = bytearray()
    response.extend(struct.pack('>H', total_len))  # TPKT
    response.extend([0x00, 0x00, 0x00, 0x00])  # padding
    response.extend([
        0x02, 0xF0, 0x80,  # COTP DT
        0x32, 0x07, 0x00, 0x00,  # S7 header
        (len(resp_data) + 4) >> 8, (len(resp_data) + 4) & 0xFF,
        0x00, 0x00,
        0x00, 0x00, 0x00, 0x0E, 0x00, 0x00,
    ])
    response.extend(resp_data)

    header = struct.pack('>H', len(response))
    response[0:2] = header
    return bytes(response)


DATA_BLOCKS = {
    1: {i: 0 for i in range(256)},
    2: {i: 0 for i in range(256)},
    3: {i: 0 for i in range(256)},
}

BLOCK_NAMES = {
    1: "ProcessValues",
    2: "Setpoints",
    3: "Diagnostics",
}


def _init_data_blocks():
    """Initialize realistic values."""
    db1 = DATA_BLOCKS[1]
    db1[0] = 235   # Reactor temp (C*10)
    db1[1] = 450   # Pressure (bar*100)
    db1[2] = 780   # Tank level (0-1000)
    db1[4] = 1200  # Flow rate (L/min)
    db1[6] = 75    # Valve position (%)
    db1[8] = 1450  # Pump speed (RPM)
    db1[10] = 1    # System online
    db1[12] = 450  # Power (kW)

    db2 = DATA_BLOCKS[2]
    db2[0] = 240   # Temp setpoint
    db2[2] = 50    # Pressure setpoint
    db2[4] = 75    # Level setpoint
    db2[6] = 1000  # Flow setpoint
    db2[8] = 70    # Valve setpoint

    db3 = DATA_BLOCKS[3]
    db3[0] = 0     # Error code
    db3[2] = time.time()
    db3[4] = 0     # Warning count
    db3[6] = 0     # Alarm count
    db3[8] = 1     # Safety armed


def s7_write_response(data, db_values):
    """Build S7 write response."""
    if len(data) < 22:
        return None
    # Simplified: return success
    return bytes([
        0x03, 0x00, 0x00, 0x16,
        0x02, 0xF0, 0x80,
        0x32, 0x06, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x0E,
        0x00, 0x00, 0x00, 0x01,
        0x00, 0x00, 0xFF,
    ])


def handle_s7_client(conn, addr):
    """Handle a single S7 client connection."""
    log.info(f"S7 connection from {addr}")
    state = "cotp"

    try:
        while True:
            data = conn.recv(S7_PDU_SIZE)
            if not data:
                break

            if state == "cotp":
                if data[4:5] == b'\x11' and data[5:6] == b'\xE0':
                    conn.send(s7_cotp_cc())
                    state = "s7_setup"
                else:
                    conn.send(s7_cotp_cc())
                    state = "s7_setup"

            elif state == "s7_setup":
                if len(data) > 21 and data[21] == 0xF0:
                    conn.send(s7_setup_comm())
                    state = "ready"
                    log.info(f"S7 client {addr} initialized")
                else:
                    conn.send(s7_setup_comm())
                    state = "ready"

            elif state == "ready":
                if len(data) < 22:
                    continue
                func = data[22] if len(data) > 22 else None
                if func == 0x04:  # Read
                    resp = s7_read_response(data, DATA_BLOCKS)
                    if resp:
                        conn.send(resp)
                elif func == 0x05:  # Write
                    # Parse write (simplified)
                    log.info(f"S7 write request from {addr}")
                    conn.send(s7_write_response(data, DATA_BLOCKS))
                elif func == 0x07:  # SZL
                    pass  # Ignore
                else:
                    log.debug(f"S7 unknown function {func} from {addr}")

    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        log.info(f"S7 client {addr} disconnected: {e}")
    finally:
        conn.close()


def _update_process():
    """Simulate process changes."""
    import random as rnd
    db1 = DATA_BLOCKS[1]
    db1[0] = max(100, min(500, db1[0] + rnd.gauss(0, 0.5)))
    db1[1] = max(0, min(800, db1[1] + rnd.gauss(0, 0.8)))
    db1[2] = max(0, min(1000, db1[2] - 0.5 + rnd.gauss(0, 0.2)))
    db1[4] = max(0, min(2000, db1[4] + rnd.gauss(0, 3)))


def run_s7_sim(host="0.0.0.0", port=8102):
    """Run the S7 protocol simulator."""
    _init_data_blocks()

    # Process update thread
    def process_loop():
        while True:
            _update_process()
            time.sleep(2)

    t = threading.Thread(target=process_loop, daemon=True)
    t.start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    server.settimeout(1.0)

    log.info(f"S7 simulator listening on {host}:{port}")

    try:
        while True:
            try:
                conn, addr = server.accept()
                t = threading.Thread(
                    target=handle_s7_client, args=(conn, addr), daemon=True
                )
                t.start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
