"""
opcua_sim.py — OPC UA Server Simulator
Simulates an industrial OPC UA server with process variables.
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import math
import time
import random
import logging
import threading

log = logging.getLogger("opcua_sim")


def run_opcua_sim(endpoint="opc.tcp://0.0.0.0:4840"):
    """Run the OPC UA simulator server."""
    try:
        from asyncua import Server, ua
    except ImportError:
        log.warning("asyncua not available, running fallback")
        _run_fallback_opcua(endpoint)
        return

    server = Server()
    try:
        server.set_endpoint(endpoint)
        server.set_server_name("OT-Lab-OPCUA-Server")
        server.set_security_policy([
            ua.SecurityPolicyType.NoSecurity,
            ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
        ])

        # Register namespace
        uri = "http://ot-lab.opcua/simulation"
        idx = server.register_namespace(uri)

        # Create object structure
        objects = server.get_objects_node()

        # Process Cell
        reactor = objects.add_object(idx, "ReactorCell")
        temp_sensor = reactor.add_variable(idx, "Temperature", 235.0)
        temp_sensor.set_writable(True)
        pressure_sensor = reactor.add_variable(idx, "Pressure", 45.0)
        pressure_sensor.set_writable(True)
        level_sensor = reactor.add_variable(idx, "Level", 78.0)
        level_sensor.set_writable(True)

        # Piping System
        piping = objects.add_object(idx, "PipingSystem")
        flow_rate = piping.add_variable(idx, "FlowRate", 1200.0)
        flow_rate.set_writable(True)
        valve_position = piping.add_variable(idx, "ValvePosition", 75.0)
        valve_position.set_writable(True)

        # Power System
        power = objects.add_object(idx, "PowerSystem")
        total_power = power.add_variable(idx, "TotalPowerKW", 450.0)
        total_power.set_writable(True)
        motor_speed = power.add_variable(idx, "MotorSpeedRPM", 1450.0)
        motor_speed.set_writable(True)

        # Safety System
        safety = objects.add_object(idx, "SafetySystem")
        safety_status = safety.add_variable(idx, "SafetyArmed", True)
        safety_status.set_writable(True)
        alarm_status = safety.add_variable(idx, "AlarmActive", False)
        alarm_status.set_writable(True)
        emergency_stop = safety.add_variable(idx, "EmergencyStop", False)
        emergency_stop.set_writable(True)

        # Diagnostics
        diagnostics = objects.add_object(idx, "Diagnostics")
        uptime = diagnostics.add_variable(idx, "UptimeSeconds", 0.0)
        uptime.set_writable(False)
        last_maintenance = diagnostics.add_variable(
            idx, "LastMaintenance", "2024-06-15 08:00:00"
        )
        last_maintenance.set_writable(True)

        tag_metadata = {
            "Temperature": {"unit": "°C", "min": 100, "max": 500, "alarm_high": 400},
            "Pressure": {"unit": "bar", "min": 0, "max": 80, "alarm_high": 65},
            "FlowRate": {"unit": "L/min", "min": 0, "max": 2000, "alarm_low": 100},
            "ValvePosition": {"unit": "%", "min": 0, "max": 100},
            "MotorSpeedRPM": {"unit": "RPM", "min": 0, "max": 3600},
        }

        for name, meta in tag_metadata.items():
            meta_node = objects.add_object(idx, f"{name}_Meta")
            for k, v in meta.items():
                prop = meta_node.add_variable(idx, k, str(v) if not isinstance(v, (int, float)) else v)
                prop.set_writable(False)

        server.start()
        log.info(f"OPC UA server started on {endpoint}")

        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            uptime.set_value(elapsed)

            temp = 235 + 15 * math.sin(elapsed * 0.01) + random.gauss(0, 0.5)
            temp_sensor.set_value(round(max(100, min(500, temp)), 1))

            pressure = 45 + 5 * math.sin(elapsed * 0.008) + random.gauss(0, 0.3)
            pressure_sensor.set_value(round(max(0, min(80, pressure)), 1))

            level = 78 - 0.02 + random.gauss(0, 0.1)
            level_sensor.set_value(round(max(0, min(100, level)), 1))

            flow = 1200 + 50 * math.sin(elapsed * 0.005) + random.gauss(0, 5)
            flow_rate.set_value(round(max(0, min(2000, flow)), 1))

            speed = 1450 + 20 * math.sin(elapsed * 0.003) + random.gauss(0, 2)
            motor_speed.set_value(round(max(0, min(3600, speed)), 1))

            time.sleep(0.5)

    except Exception as e:
        log.error(f"OPC UA server error: {e}")
        try:
            server.stop()
        except Exception:
            pass
        _run_fallback_opcua(endpoint)


def _run_fallback_opcua(endpoint="opc.tcp://0.0.0.0:4840"):
    """Fallback OPC UA simulation via HTTP."""
    from flask import Flask, jsonify

    app = Flask("opcua-fallback")
    variables = {
        "ReactorCell.Temperature": {"value": 235.0, "unit": "°C"},
        "ReactorCell.Pressure": {"value": 45.0, "unit": "bar"},
        "PipingSystem.FlowRate": {"value": 1200.0, "unit": "L/min"},
        "PipingSystem.ValvePosition": {"value": 75.0, "unit": "%"},
        "PowerSystem.TotalPowerKW": {"value": 450.0, "unit": "kW"},
        "SafetySystem.SafetyArmed": {"value": True},
    }

    @app.route("/opcua/variables")
    def list_vars():
        return jsonify(variables)

    @app.route("/opcua/read/<path:varname>")
    def read_var(varname):
        varname = varname.replace("/", ".")
        if varname in variables:
            return jsonify({"name": varname, **variables[varname]})
        return jsonify({"error": "not found"}), 404

    def update_loop():
        import random as rnd
        while True:
            for key in variables:
                if "Temperature" in key:
                    drift = rnd.gauss(0, 0.3)
                    variables[key]["value"] = round(max(100, min(500, float(variables[key]["value"]) + drift)), 1)
                elif "Pressure" in key:
                    drift = rnd.gauss(0, 0.2)
                    variables[key]["value"] = round(max(0, min(80, float(variables[key]["value"]) + drift)), 1)
                elif "FlowRate" in key:
                    drift = rnd.gauss(0, 3)
                    variables[key]["value"] = round(max(0, min(2000, float(variables[key]["value"]) + drift)), 1)
            time.sleep(2)

    t = threading.Thread(target=update_loop, daemon=True)
    t.start()

    log.info(f"OPC UA fallback HTTP simulator on port 8484")
    app.run(host="0.0.0.0", port=8484)
