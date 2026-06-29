"""
mqtt_sim.py — MQTT Telemetry Simulator
Publishes realistic OT telemetry data to MQTT topics.
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import math
import time
import json
import random
import logging
import threading

log = logging.getLogger("mqtt_sim")

TELEMETRY_TOPICS = {
    "ot/plant1/reactor/temperature": {
        "base": 235, "range": 15, "unit": "C", "period": 0.01,
    },
    "ot/plant1/reactor/pressure": {
        "base": 45, "range": 5, "unit": "bar", "period": 0.008,
    },
    "ot/plant1/reactor/level": {
        "base": 78, "range": 3, "unit": "%", "period": 0.002,
    },
    "ot/plant1/piping/flow_rate": {
        "base": 1200, "range": 50, "unit": "L/min", "period": 0.005,
    },
    "ot/plant1/piping/valve_position": {
        "base": 75, "range": 5, "unit": "%", "period": 0.001,
    },
    "ot/plant1/pump/speed": {
        "base": 1450, "range": 20, "unit": "RPM", "period": 0.003,
    },
    "ot/plant1/pump/power": {
        "base": 200, "range": 10, "unit": "kW", "period": 0.004,
    },
    "ot/plant1/environment/temperature": {
        "base": 32, "range": 5, "unit": "C", "period": 0.002,
    },
    "ot/plant1/environment/humidity": {
        "base": 55, "range": 10, "unit": "%", "period": 0.001,
    },
}

COMMAND_TOPICS = [
    "ot/plant1/cmd/pump/start",
    "ot/plant1/cmd/pump/stop",
    "ot/plant1/cmd/valve/set",
    "ot/plant1/cmd/emergency/stop",
    "ot/plant1/cmd/setpoint/temperature",
]

ALARM_TOPICS = [
    "ot/plant1/alarm/high_temperature",
    "ot/plant1/alarm/low_pressure",
    "ot/plant1/alarm/pump_fault",
    "ot/plant1/alarm/emergency",
    "ot/plant1/alarm/communication_loss",
]

STATUS_TOPICS = [
    "ot/plant1/status/system",
    "ot/plant1/status/pump",
    "ot/plant1/status/safety",
    "ot/plant1/status/network",
]


def run_mqtt_sim(broker="mosquitto", port=1883):
    """Run the MQTT telemetry simulator."""
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        log.error("paho-mqtt not available")
        return

    client = mqtt.Client(client_id="ot-simulator", protocol=mqtt.MQTTv311)
    client.enable_logger()

    connected = threading.Event()

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            log.info(f"MQTT connected to {broker}:{port}")
            connected.set()
            # Subscribe to command topics
            for topic in COMMAND_TOPICS:
                c.subscribe(topic, qos=1)
                log.info(f"Subscribed to {topic}")
        else:
            log.error(f"MQTT connection failed with code {rc}")

    def on_message(c, userdata, msg):
        log.info(f"MQTT command received: {msg.topic} -> {msg.payload.decode()}")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        log.error(f"MQTT connection failed: {e}")
        return

    client.loop_start()

    if not connected.wait(timeout=10):
        log.warning("MQTT connection timeout, starting anyway")

    start_time = time.time()
    publish_count = 0

    while True:
        try:
            elapsed = time.time() - start_time

            # Publish telemetry
            for topic, config in TELEMETRY_TOPICS.items():
                value = (
                    config["base"]
                    + config["range"] * math.sin(elapsed * config["period"] * 2 * 3.14159)
                    + random.gauss(0, 0.5)
                )
                payload = json.dumps({
                    "value": round(value, 2),
                    "unit": config["unit"],
                    "timestamp": time.time(),
                    "quality": random.choice(["good", "good", "good", "uncertain"]),
                })
                client.publish(topic, payload, qos=1)
                publish_count += 1

            # Publish status (every 5s)
            if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                for topic in STATUS_TOPICS:
                    status_payload = json.dumps({
                        "status": "operational",
                        "uptime": int(elapsed),
                        "last_seen": time.time(),
                        "mode": "auto",
                    })
                    client.publish(topic, status_payload, qos=1, retain=True)

            # Publish heartbeats
            client.publish(
                "ot/plant1/heartbeat",
                json.dumps({"ts": time.time(), "seq": publish_count}),
                qos=0,
            )

            time.sleep(1)

        except Exception as e:
            log.error(f"MQTT publish error: {e}")
            time.sleep(5)
