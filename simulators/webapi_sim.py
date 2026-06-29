"""
webapi_sim.py — Web API Simulator (SCADA REST API)
Simulates a SCADA system's REST API for monitoring and control.
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import time
import json
import random
import logging
import threading
from flask import Flask, jsonify, request

log = logging.getLogger("webapi_sim")

app = Flask("webapi-sim")

# Simulated SCADA database
SCADA_DATA = {
    "reactor": {
        "temperature": {"value": 235.0, "unit": "°C", "alarm_high": 400, "alarm_low": 100},
        "pressure": {"value": 45.0, "unit": "bar", "alarm_high": 65, "alarm_low": 0},
        "level": {"value": 78.0, "unit": "%", "alarm_high": 90, "alarm_low": 10},
        "status": "running",
    },
    "piping": {
        "flow_rate": {"value": 1200.0, "unit": "L/min", "alarm_high": 1800, "alarm_low": 100},
        "valve_position": {"value": 75.0, "unit": "%"},
        "status": "running",
    },
    "pump": {
        "speed": {"value": 1450.0, "unit": "RPM", "alarm_high": 3500},
        "power": {"value": 200.0, "unit": "kW"},
        "status": "running",
        "motor_current": {"value": 35.0, "unit": "A"},
    },
    "power": {
        "total": {"value": 450.0, "unit": "kW"},
        "heater": {"value": 150.0, "unit": "kW"},
        "control": {"value": 100.0, "unit": "kW"},
        "status": "online",
    },
    "safety": {
        "armed": True,
        "alarm_active": False,
        "emergency_stop": False,
        "last_test": "2024-06-01T08:00:00Z",
        "status": "operational",
    },
    "environment": {
        "temperature": {"value": 32.0, "unit": "°C"},
        "humidity": {"value": 55.0, "unit": "%"},
    },
}

AUDIT_LOG = []


@app.route("/api/v1/health")
def api_health():
    return jsonify({"status": "healthy", "service": "scada-webapi"})


@app.route("/api/v1/points")
def list_points():
    """List all SCADA points."""
    result = {}
    for category, points in SCADA_DATA.items():
        for point_name, point_data in points.items():
            if isinstance(point_data, dict) and "value" in point_data:
                key = f"{category}.{point_name}"
                result[key] = {
                    "value": point_data["value"],
                    "unit": point_data.get("unit", ""),
                    "alarm_high": point_data.get("alarm_high"),
                    "alarm_low": point_data.get("alarm_low"),
                }
            elif isinstance(point_data, bool):
                key = f"{category}.{point_name}"
                result[key] = {"value": point_data, "type": "boolean"}
            elif isinstance(point_data, str):
                key = f"{category}.{point_name}"
                result[key] = {"value": point_data, "type": "string"}
    return jsonify(result)


@app.route("/api/v1/read/<path:point_path>")
def read_point(point_path):
    """Read a specific SCADA point."""
    parts = point_path.split(".")
    if len(parts) == 2:
        category, point = parts
        if category in SCADA_DATA and point in SCADA_DATA[category]:
            data = SCADA_DATA[category][point]
            return jsonify({
                "point": point_path,
                **({"value": data["value"], "unit": data.get("unit", "")}
                   if isinstance(data, dict) and "value" in data
                   else {"value": data}),
                "timestamp": time.time(),
            })
    return jsonify({"error": "point not found"}), 404


@app.route("/api/v1/write/<path:point_path>", methods=["POST"])
def write_point(point_path):
    """Write to a SCADA setpoint."""
    parts = point_path.split(".")
    if len(parts) != 2:
        return jsonify({"error": "invalid point"}), 400

    category, point = parts
    if category not in SCADA_DATA or point not in SCADA_DATA[category]:
        return jsonify({"error": "point not found"}), 404

    data = request.get_json()
    if "value" not in data:
        return jsonify({"error": "value required"}), 400

    point_data = SCADA_DATA[category][point]
    if isinstance(point_data, dict) and "value" in point_data:
        old_val = point_data["value"]
        point_data["value"] = data["value"]
        log.info(f"SCADA write: {point_path} = {data['value']} (was {old_val})")

        AUDIT_LOG.append({
            "timestamp": time.time(),
            "action": "write",
            "point": point_path,
            "old_value": old_val,
            "new_value": data["value"],
            "source": request.remote_addr,
        })

        return jsonify({"status": "ok", "point": point_path, "value": data["value"]})

    return jsonify({"error": "point not writable"}), 400


@app.route("/api/v1/alarms")
def list_alarms():
    """List active alarms."""
    alarms = []
    for category, points in SCADA_DATA.items():
        for point_name, point_data in points.items():
            if isinstance(point_data, dict) and "value" in point_data:
                val = point_data["value"]
                if "alarm_high" in point_data and val > point_data["alarm_high"]:
                    alarms.append({
                        "point": f"{category}.{point_name}",
                        "type": "high",
                        "value": val,
                        "threshold": point_data["alarm_high"],
                    })
                if "alarm_low" in point_data and val < point_data["alarm_low"]:
                    alarms.append({
                        "point": f"{category}.{point_name}",
                        "type": "low",
                        "value": val,
                        "threshold": point_data["alarm_low"],
                    })

    if SCADA_DATA["safety"]["alarm_active"]:
        alarms.append({
            "point": "safety.alarm_active",
            "type": "safety",
            "value": True,
            "message": "Safety alarm is active!",
        })

    return jsonify({"alarms": alarms, "count": len(alarms)})


@app.route("/api/v1/audit")
def audit_log():
    """Return recent audit events."""
    return jsonify(AUDIT_LOG[-100:])


@app.route("/api/v1/status")
def system_status():
    """Return overall system status."""
    return jsonify({
        "system": SCADA_DATA["power"]["status"],
        "reactor": SCADA_DATA["reactor"]["status"],
        "piping": SCADA_DATA["piping"]["status"],
        "pump": SCADA_DATA["pump"]["status"],
        "safety": SCADA_DATA["safety"]["status"],
        "alarm": SCADA_DATA["safety"]["alarm_active"],
        "uptime": time.time(),
    })


def update_process():
    """Simulate process changes."""
    import random as rnd
    r = SCADA_DATA["reactor"]
    r["temperature"]["value"] = round(max(100, min(500,
        r["temperature"]["value"] + rnd.gauss(0, 0.3))), 1)
    r["pressure"]["value"] = round(max(0, min(80,
        r["pressure"]["value"] + rnd.gauss(0, 0.2))), 1)
    r["level"]["value"] = round(max(0, min(100,
        r["level"]["value"] - 0.02 + rnd.gauss(0, 0.1))), 1)

    p = SCADA_DATA["piping"]
    p["flow_rate"]["value"] = round(max(0, min(2000,
        p["flow_rate"]["value"] + rnd.gauss(0, 5))), 1)

    pu = SCADA_DATA["pump"]
    pu["speed"]["value"] = round(max(0, min(3600,
        pu["speed"]["value"] + rnd.gauss(0, 2))), 1)
    pu["motor_current"]["value"] = round(max(0, min(100,
        pu["motor_current"]["value"] + rnd.gauss(0, 0.3))), 1)

    pw = SCADA_DATA["power"]
    pw["total"]["value"] = round(max(0, pw["total"]["value"] + rnd.gauss(0, 1)), 1)


def run_webapi_sim(host="0.0.0.0", port=8082):
    """Run the WebAPI SCADA simulator."""

    def process_loop():
        while True:
            update_process()
            time.sleep(2)

    t = threading.Thread(target=process_loop, daemon=True)
    t.start()

    log.info(f"WebAPI SCADA simulator starting on {host}:{port}")
    from werkzeug.serving import run_simple
    run_simple(host, port, app)
