"""
practice_lab.py — Safe OT Protocol Practice Area
Isolated sandbox for learning and experimenting with OT protocols.
NOT connected to the main lab environment.

IMPORTANT: This practice area is for EDUCATIONAL USE ONLY.
Never use these techniques against real industrial systems.

The practice area provides:
- Modbus TCP playground (port 5021)
- OPC UA playground (port 4841)
- Protocol reference and examples
- Traffic capture and analysis
- Guided exercises
"""
import json
import logging
import random
import threading
import time
from flask import Flask, jsonify, request, render_template_string

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [practice] %(levelname)s: %(message)s",
)
log = logging.getLogger("practice_lab")

app = Flask(__name__)

PRACTICE_TOPICS = {
    "practice/temperature": {"description": "Simulated temperature sensor", "value": 25.0},
    "practice/pressure": {"description": "Simulated pressure sensor", "value": 1.0},
    "practice/flow": {"description": "Simulated flow meter", "value": 100.0},
    "practice/valve": {"description": "Simulated valve position", "value": 50.0},
    "practice/pump": {"description": "Simulated pump status", "value": "stopped"},
}

EXERCISES = [
    {
        "id": "modbus-basics",
        "title": "Modbus Basics",
        "description": "Learn to read and write Modbus registers using Python and command-line tools.",
        "protocol": "modbus",
        "port": 5021,
        "steps": [
            "Connect to the Modbus practice server on port 5021",
            "Read holding register 0 (temperature)",
            "Write value 75 to holding register 4 (valve position)",
            "Read coils 0-7 and identify which are on/off",
            "Try writing to a read-only register and observe the error",
        ],
        "hint": "Use pymodbus: `client = ModbusTcpClient('safe-practice', port=5021)`",
        "safety_note": "All practice is in an isolated sandbox. No real devices are affected.",
    },
    {
        "id": "mqtt-explore",
        "title": "MQTT Exploration",
        "description": "Subscribe to topics, publish messages, and understand MQTT patterns.",
        "protocol": "mqtt",
        "broker": "mosquitto",
        "port": 1883,
        "steps": [
            "Subscribe to 'practice/#' wildcard topic",
            "Observe the telemetry data being published",
            "Publish a message to 'practice/valve' with position 75",
            "Read the retained message on 'practice/pump'",
            "Explore different QoS levels and their effects",
        ],
        "hint": "mosquitto_sub -h safe-practice -t 'practice/#' -v",
        "safety_note": "MQTT is isolated to the lab network. No external connectivity.",
    },
    {
        "id": "packet-analysis",
        "title": "Packet Capture & Analysis",
        "description": "Capture and analyze OT protocol traffic using tcpdump and Python.",
        "protocol": "general",
        "steps": [
            "Run tcpdump on the practice network interface",
            "Generate practice Modbus traffic from the exercise terminal",
            "Save the capture to a PCAP file",
            "Analyze the PCAP with tcpdump or Wireshark",
            "Identify the Modbus function codes and register values in the capture",
        ],
        "hint": "tcpdump -i any port 5021 -w practice.pcap",
        "safety_note": "Only capture traffic within the isolated Docker network.",
    },
    {
        "id": "protocol-fuzzing",
        "title": "Safe Protocol Fuzzing",
        "description": "Send malformed protocol messages and observe responses in a safe environment.",
        "protocol": "modbus",
        "port": 5021,
        "steps": [
            "Send a Modbus request with invalid function code 0xFF",
            "Send a request with an out-of-bounds register address (9999)",
            "Send a malformed packet (truncated header)",
            "Observe how the server handles each invalid request",
            "Document which errors reveal information about the server",
        ],
        "hint": "Use raw sockets to craft custom Modbus frames.",
        "safety_note": "Fuzzing is only safe in this isolated environment.",
    },
    {
        "id": "process-simulation",
        "title": "Process Simulation",
        "description": "Build your own simple process simulation and practice monitoring it.",
        "protocol": "general",
        "steps": [
            "Use the practice HTTP API to create custom tags",
            "Simulate a simple tank filling/emptying process",
            "Add noise and drift to your simulation",
            "Monitor the process through the API",
            "Write a script that detects anomalies in your simulation",
        ],
        "hint": "POST to /practice/tags to create custom tags.",
        "safety_note": "Your custom simulation runs in memory only.",
    },
]

# Custom practice tags (user-created)
custom_tags = {}
practice_lock = threading.Lock()

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OT Practice Lab — Safe Protocol Sandbox</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0a0e17; color: #e0e6f0; }
        .card { background: #131a2b; border-color: #1e2a3e; }
        .card-header { background: rgba(0,0,0,0.2); border-color: #1e2a3e; }
        code { color: #00d4ff; background: rgba(0,212,255,0.1); padding: 2px 6px; border-radius: 3px; }
        .banner { background: linear-gradient(90deg, #1a0000, #3a0000); color: #ff6b6b; text-align: center; padding: 8px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="banner">
        ⚠ SAFE PRACTICE AREA — ISOLATED SANDBOX — NEVER USE ON REAL SYSTEMS ⚠
    </div>
    <div class="container py-4">
        <h1 class="mb-2"><i class="bi bi-shield-check text-success"></i> OT Safe Practice Lab</h1>
        <p class="text-secondary mb-4">Isolated sandbox for protocol exploration and defensive testing.</p>

        <div class="alert alert-success border-2">
            <strong>Safe Environment:</strong> This practice area is completely isolated from the main lab.
            No data or commands from this area can affect the simulation environment.
            Use it freely to learn and experiment.
        </div>

        <h3 class="mt-4"><i class="bi bi-list-check text-info"></i> Guided Exercises</h3>
        <div class="row g-3 mb-4">
            {% for ex in exercises %}
            <div class="col-md-6 col-lg-4">
                <div class="card h-100">
                    <div class="card-body">
                        <h5>{{ ex.title }}</h5>
                        <p class="text-secondary small">{{ ex.description }}</p>
                        <span class="badge bg-info">{{ ex.protocol }}</span>
                        {% if ex.port %}
                        <span class="badge bg-secondary">Port {{ ex.port }}</span>
                        {% endif %}
                        <hr class="border-secondary">
                        <ol class="text-secondary small mb-2">
                            {% for step in ex.steps[:3] %}
                            <li>{{ step }}</li>
                            {% endfor %}
                        </ol>
                        <div class="collapse" id="steps{{ loop.index }}">
                            <ol start="4" class="text-secondary small mb-2">
                                {% for step in ex.steps[3:] %}
                                <li>{{ step }}</li>
                                {% endfor %}
                            </ol>
                            <div class="alert alert-info small py-2">
                                <strong>Hint:</strong> {{ ex.hint }}
                            </div>
                            <div class="alert alert-warning small py-2">
                                <strong>Safety:</strong> {{ ex.safety_note }}
                            </div>
                        </div>
                        <button class="btn btn-sm btn-outline-info mt-2" type="button"
                                data-bs-toggle="collapse" data-bs-target="#steps{{ loop.index }}">
                            Show More <i class="bi bi-chevron-down ms-1"></i>
                        </button>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <h3><i class="bi bi-diagram-3 text-warning"></i> Practice Topics</h3>
        <div class="card mb-4">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-dark table-sm">
                        <thead>
                            <tr>
                                <th>Topic</th>
                                <th>Description</th>
                                <th>Current Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for topic, data in topics.items() %}
                            <tr>
                                <td><code>{{ topic }}</code></td>
                                <td>{{ data.description }}</td>
                                <td>{{ data.value }}</td>
                            </tr>
                            {% endfor %}
                            {% for tag, data in custom_tags.items() %}
                            <tr class="table-info">
                                <td><code>{{ tag }}</code></td>
                                <td>Custom tag</td>
                                <td>{{ data }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <h3><i class="bi bi-gear text-success"></i> API Endpoints</h3>
        <div class="card">
            <div class="card-body">
                <ul class="list-unstyled small">
                    <li class="mb-2"><code>GET /health</code> — Health check</li>
                    <li class="mb-2"><code>GET /explore</code> — Practice topics</li>
                    <li class="mb-2"><code>POST /practice/tags</code> — Create custom tag</li>
                    <li class="mb-2"><code>DELETE /practice/tags/&lt;name&gt;</code> — Delete custom tag</li>
                    <li><code>GET /exercises</code> — Exercise list</li>
                </ul>
            </div>
        </div>

        <div class="alert alert-danger mt-4 border-2">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            <strong>⚠ REMINDER:</strong> All exercises in this practice area are for
            <strong>educational purposes only</strong>. Never perform these activities
            against real industrial control systems, production networks, or any system
            you do not own or have explicit written permission to test.
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


@app.route("/")
def index():
    with practice_lock:
        return render_template_string(
            INDEX_HTML,
            exercises=EXERCISES,
            topics=PRACTICE_TOPICS,
            custom_tags=custom_tags,
        )


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "ot-safe-practice",
        "isolated": True,
        "warning": "FOR EDUCATIONAL USE ONLY — NEVER USE ON REAL SYSTEMS",
    })


@app.route("/explore")
def explore():
    """Return all current practice topics and their values."""
    with practice_lock:
        result = dict(PRACTICE_TOPICS)
        result.update({f"custom:{k}": v for k, v in custom_tags.items()})
    return jsonify(result)


@app.route("/practice/tags", methods=["POST"])
def create_tag():
    """Create a custom practice tag."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name required"}), 400
    name = data["name"]
    value = data.get("value", 0)
    with practice_lock:
        custom_tags[name] = value
    log.info(f"Custom tag created: {name} = {value}")
    return jsonify({"status": "ok", "name": name, "value": value})


@app.route("/practice/tags/<name>", methods=["DELETE"])
def delete_tag(name):
    """Delete a custom practice tag."""
    with practice_lock:
        if name in custom_tags:
            del custom_tags[name]
            return jsonify({"status": "deleted"})
    return jsonify({"error": "not found"}), 404


@app.route("/practice/tags/<name>", methods=["PUT"])
def update_tag(name):
    """Update a custom practice tag value."""
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"error": "value required"}), 400
    with practice_lock:
        custom_tags[name] = data["value"]
    return jsonify({"status": "ok", "name": name, "value": data["value"]})


@app.route("/exercises")
def list_exercises():
    """Return all exercises."""
    return jsonify(EXERCISES)


@app.route("/exercise/<exercise_id>")
def get_exercise(exercise_id):
    """Return a specific exercise."""
    for ex in EXERCISES:
        if ex["id"] == exercise_id:
            return jsonify(ex)
    return jsonify({"error": "not found"}), 404


def run_modbus_practice():
    """Run a practice Modbus server on port 5021."""
    try:
        from pymodbus.server import StartTcpServer
        from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
        from pymodbus.datastore.store import ModbusSparseDataBlock

        hr = ModbusSparseDataBlock({i: i * 10 for i in range(50)})
        hr.values.update({
            0: 250,   # Temperature * 10
            1: 100,   # Pressure * 100
            2: 500,   # Level * 10
            3: 1000,  # Flow rate
            4: 50,    # Valve position
            5: 0,     # Mode (0=manual, 1=auto)
        })
        coils = ModbusSparseDataBlock({i: (i % 2 == 0) for i in range(20)})

        store = ModbusSlaveContext(hr=hr, co=coils)
        context = ModbusServerContext(slaves=store, single=True)

        log.info("Modbus practice server on port 5021")
        StartTcpServer(context=context, address=("0.0.0.0", 5021))
    except Exception as e:
        log.error(f"Modbus practice error: {e}")


def publish_practice_mqtt():
    """Publish practice data to MQTT topics."""
    try:
        import paho.mqtt.client as mqtt
        client = mqtt.Client(client_id="practice-publisher")
        client.connect("mosquitto", 1883, 60)

        while True:
            import random as rnd
            for topic, data in PRACTICE_TOPICS.items():
                if isinstance(data["value"], (int, float)):
                    val = data["value"] + rnd.gauss(0, 0.5)
                    payload = json.dumps({
                        "value": round(val, 2),
                        "timestamp": time.time(),
                        "practice_mode": True,
                    })
                else:
                    payload = json.dumps({
                        "value": data["value"],
                        "timestamp": time.time(),
                        "practice_mode": True,
                    })
                client.publish(topic, payload, qos=0)
            time.sleep(2)
    except Exception as e:
        log.warning(f"Practice MQTT publish not available: {e}")


def run_opcua_practice():
    """Run an OPC UA practice server on port 4841."""
    try:
        from asyncua import Server, ua
        server = Server()
        server.set_endpoint("opc.tcp://0.0.0.0:4841")
        server.set_server_name("OT-Lab-Practice")

        idx = server.register_namespace("http://ot-lab.practice")
        objects = server.get_objects_node()

        practice_vars = {}
        for name, info in {
            "Temperature": 25.0,
            "Pressure": 1.0,
            "Flow": 100.0,
            "ValvePosition": 50.0,
            "PumpSpeed": 0.0,
        }.items():
            var = objects.add_variable(idx, name, info)
            var.set_writable(True)
            practice_vars[name] = var

        server.start()
        log.info("OPC UA practice server on port 4841")

        while True:
            for name, var in practice_vars.items():
                if name not in ("ValvePosition", "PumpSpeed"):
                    current = var.get_value()
                    new_val = current + random.gauss(0, 0.2)
                    var.set_value(round(new_val, 2))
            time.sleep(2)

    except Exception as e:
        log.warning(f"OPC UA practice server not available: {e}")


def main():
    log.info("=" * 60)
    log.info("OT Safe Practice Lab Starting")
    log.info("FOR ISOLATED EDUCATIONAL USE ONLY")
    log.info("=" * 60)

    # Start Modbus practice server
    t1 = threading.Thread(target=run_modbus_practice, daemon=True)
    t1.start()

    # Start OPC UA practice server
    t2 = threading.Thread(target=run_opcua_practice, daemon=True)
    t2.start()

    # Start MQTT practice publisher
    t3 = threading.Thread(target=publish_practice_mqtt, daemon=True)
    t3.start()

    log.info("Practice servers started:")
    log.info("  - Modbus TCP:  port 5021")
    log.info("  - OPC UA:     port 4841")
    log.info("  - MQTT:       broker mosquitto:1883 (topics: practice/#)")
    log.info("  - Web UI:     port 9090")

    app.run(host="0.0.0.0", port=9090)


if __name__ == "__main__":
    main()
