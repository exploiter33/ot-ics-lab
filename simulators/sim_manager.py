"""
sim_manager.py — OT Protocol Simulator Manager
Launches all protocol simulators as daemon threads.
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import time
import logging
import threading
import json
from flask import Flask, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("sim_manager")

health_app = Flask(__name__)

SIMULATORS = {}
HEALTH = {"status": "starting", "simulators": {}}


@health_app.route("/health")
def health():
    return jsonify(HEALTH)


@health_app.route("/status")
def status():
    results = {}
    for name, sim_data in SIMULATORS.items():
        t = sim_data.get("thread")
        results[name] = {
            "alive": t is not None and t.is_alive(),
            "last_heartbeat": sim_data.get("last_heartbeat", 0),
        }
    return jsonify(results)


def run_simulator(name, target, kwargs=None):
    """Run a simulator function in a thread with health tracking."""
    def wrapper():
        global HEALTH
        log.info(f"Starting simulator: {name}")
        try:
            target(**(kwargs or {}))
        except Exception as e:
            log.error(f"Simulator {name} died: {e}")
            HEALTH["simulators"][name] = "error"
        finally:
            log.warning(f"Simulator {name} stopped")

    t = threading.Thread(target=wrapper, daemon=True, name=name)
    t.start()
    SIMULATORS[name] = {"thread": t, "last_heartbeat": time.time()}
    HEALTH["simulators"][name] = "running"
    return t


def main():
    from modbus_sim import run_modbus_sim
    from bacnet_sim import run_bacnet_sim
    from opcua_sim import run_opcua_sim
    from mqtt_sim import run_mqtt_sim
    from s7_sim import run_s7_sim
    from enip_sim import run_enip_sim
    from webapi_sim import run_webapi_sim

    modbus_kwargs = {"host": "0.0.0.0", "port": 5020}
    bacnet_kwargs = {"host": "0.0.0.0"}
    opcua_kwargs = {"endpoint": "opc.tcp://0.0.0.0:4840"}
    mqtt_kwargs = {"broker": "mosquitto", "port": 1883}
    s7_kwargs = {"host": "0.0.0.0", "port": 8102}
    enip_kwargs = {"host": "0.0.0.0", "port": 44818}
    webapi_kwargs = {"host": "0.0.0.0", "port": 8082}

    threads = [
        run_simulator("modbus", run_modbus_sim, modbus_kwargs),
        run_simulator("bacnet", run_bacnet_sim, bacnet_kwargs),
        run_simulator("opcua", run_opcua_sim, opcua_kwargs),
        run_simulator("mqtt", run_mqtt_sim, mqtt_kwargs),
        run_simulator("s7", run_s7_sim, s7_kwargs),
        run_simulator("enip", run_enip_sim, enip_kwargs),
        run_simulator("webapi", run_webapi_sim, webapi_kwargs),
    ]

    log.info(f"Launched {len(threads)} simulator threads")

    HEALTH["status"] = "running"

    try:
        from werkzeug.serving import run_simple
        run_simple("0.0.0.0", 9099, health_app)
    except ImportError:
        health_app.run(host="0.0.0.0", port=9099)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
