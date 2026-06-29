"""
modbus_sim.py — Modbus TCP Simulator
Simulates a realistic industrial process with sensors and actuators.
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import time
import random
import logging
import struct
from threading import Lock

from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore.store import ModbusSparseDataBlock

log = logging.getLogger("modbus_sim")


class ProcessDataBlock(ModbusSparseDataBlock):
    """Simulates process values in holding registers (FC3/FC6/FC16)."""

    def __init__(self):
        super().__init__({i: 0 for i in range(0, 100)})
        self.lock = Lock()
        self._init_values()

    def _init_values(self):
        self.values = {
            # Temperature sensors (0-9) — °C * 10
            0: 235,   # Reactor temp
            1: 221,   # Pipe temp
            2: 198,   # Cooling loop temp
            3: 250,   # Exhaust temp
            4: 215,   # Input feed temp
            # Pressure sensors (10-19) — bar * 100
            10: 450,  # Main pressure
            11: 380,  # Pipe pressure
            12: 120,  # Cooling pressure
            13: 510,  # Reactor pressure
            14: 200,  # Feed pressure
            # Valve positions (20-29) — 0-100%
            20: 75,   # Main valve
            21: 50,   # Bypass valve
            22: 0,    # Emergency vent
            23: 100,  # Feed valve
            24: 30,   # Cooling valve
            # Pump speeds (30-39) — RPM
            30: 1450, # Main pump
            31: 0,    # Backup pump
            32: 2800, # Booster pump
            33: 750,  # Circulation pump
            # Tank levels (40-49) — 0-1000 (0.0-100.0%)
            40: 780,  # Feed tank
            41: 450,  # Product tank
            42: 920,  # Buffer tank
            43: 300,  # Waste tank
            # Flow rates (50-59) — L/min
            50: 1200, # Main flow
            51: 450,  # Bypass flow
            52: 680,  # Cooling flow
            53: 0,    # Emergency flow
            # Power (60-64) — kW
            60: 450,  # Total power
            61: 200,  # Pump power
            62: 150,  # Heater power
            63: 100,  # Control power
            # Status flags (70-79)
            70: 1,    # System online
            71: 1,    # Main pump running
            72: 0,    # Backup pump running
            73: 1,    # Safety system armed
            74: 0,    # Alarm active
            75: 0,    # Maintenance mode
            # Coil state mirrors (80-89) — 0/1
            80: 1,    # Coil 0: Main power
            81: 0,    # Coil 1: Emergency stop
            82: 1,    # Coil 2: Heater enable
            83: 0,    # Coil 3: Alarm horn
            84: 1,    # Coil 4: Cooling enable
        }

    def __getitem__(self, key):
        with self.lock:
            if isinstance(key, slice):
                return [self.values.get(i, 0) for i in range(
                    key.start or 0, key.stop or 100, key.step or 1
                )]
            return self.values.get(key, 0)

    def __setitem__(self, key, value):
        with self.lock:
            if isinstance(key, slice):
                for i, v in enumerate(range(
                    key.start or 0, key.stop or 100, key.step or 1
                )):
                    self.values[v] = value[i] if isinstance(value, (list, tuple)) else value
            else:
                self.values[key] = value
                log.info(f"Modbus register {key} set to {value}")

    def iter_set(self, values):
        with self.lock:
            for k, v in values.items():
                self.values[k] = v

    def iter_get(self):
        with self.lock:
            return self.values.copy()

    def _update_process(self):
        """Simulate process dynamics with minor fluctuations."""
        with self.lock:
            # Temperature drifts
            for i in range(5):
                addr = i
                if addr in self.values:
                    drift = random.gauss(0, 0.5)
                    self.values[addr] = max(100, min(500, self.values[addr] + drift))

            # Flow rates fluctuate
            for addr in [50, 51, 52]:
                if addr in self.values:
                    drift = random.gauss(0, 3)
                    self.values[addr] = max(0, min(2000, self.values[addr] + drift))

            # Tank levels change
            for addr, rate in [(40, -0.5), (41, 0.3), (42, -0.1), (43, 0.2)]:
                if addr in self.values:
                    self.values[addr] = max(0, min(1000, self.values[addr] + rate + random.gauss(0, 0.2)))

            # Pressure fluctuates
            for addr in [10, 11, 12, 13, 14]:
                if addr in self.values:
                    drift = random.gauss(0, 0.8)
                    self.values[addr] = max(0, min(800, self.values[addr] + drift))


class CoilDataBlock(ModbusSparseDataBlock):
    """Simulates discrete outputs (coils)."""

    def __init__(self):
        super().__init__({i: False for i in range(0, 20)})
        self.lock = Lock()
        self.values = {i: False for i in range(20)}
        self.values[0] = True   # Main power
        self.values[2] = True   # Heater enable
        self.values[4] = True   # Cooling enable

    def __getitem__(self, key):
        with self.lock:
            if isinstance(key, slice):
                return [self.values.get(i, False) for i in range(
                    key.start or 0, key.stop or 20, key.step or 1
                )]
            return self.values.get(key, False)

    def __setitem__(self, key, value):
        with self.lock:
            if isinstance(key, slice):
                for i in range(key.start or 0, key.stop or 20, key.step or 1):
                    self.values[i] = bool(value[i] if isinstance(value, (list, tuple)) else value)
            else:
                self.values[key] = bool(value)
                log.info(f"Modbus coil {key} set to {bool(value)}")

    def iter_set(self, values):
        with self.lock:
            for k, v in values.items():
                self.values[k] = bool(v)

    def iter_get(self):
        with self.lock:
            return self.values.copy()


class DiscreteInputBlock(ModbusSparseDataBlock):
    """Simulates digital inputs from sensors."""

    def __init__(self):
        super().__init__({i: False for i in range(0, 16)})
        self.values = {i: False for i in range(16)}
        self.values[0] = True   # Power present
        self.values[1] = True   # Flow detected
        self.values[2] = False  # High temp alarm
        self.values[3] = False  # High pressure alarm
        self.values[4] = True   # Valve open
        self.values[5] = True   # Pump running

    def __getitem__(self, key):
        if isinstance(key, slice):
            return [self.values.get(i, False) for i in range(
                key.start or 0, key.stop or 16, key.step or 1
            )]
        return self.values.get(key, False)

    def __setitem__(self, key, value):
        pass  # Read-only

    def iter_set(self, values):
        pass

    def iter_get(self):
        return self.values.copy()


def run_modbus_sim(host="0.0.0.0", port=5020):
    """Run the Modbus TCP simulator."""

    process_block = ProcessDataBlock()
    coil_block = CoilDataBlock()
    discrete_block = DiscreteInputBlock()

    store = ModbusSlaveContext(
        di=discrete_block,
        co=coil_block,
        hr=process_block,
        ir=ModbusSparseDataBlock({i: i for i in range(20)}),
    )
    context = ModbusServerContext(slaves=store, single=True)

    def update_loop():
        while True:
            process_block._update_process()
            time.sleep(2)

    import threading
    t = threading.Thread(target=update_loop, daemon=True)
    t.start()

    log.info(f"Modbus simulator starting on {host}:{port}")
    StartTcpServer(
        context=context,
        address=(host, port),
        allow_reuse_address=True,
    )
