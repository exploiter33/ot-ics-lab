"""
bacnet_sim.py — BACnet/IP Simulator
Simulates building automation devices (HVAC, lighting, access control).
FOR ISOLATED EDUCATIONAL USE ONLY.
"""
import time
import random
import logging
import threading
from functools import partial

log = logging.getLogger("bacnet_sim")


def run_bacnet_sim(host="0.0.0.0"):
    """
    BACnet/IP simulator using bacpypes3.
    Creates virtual BACnet devices with realistic objects.
    """
    try:
        from bacpypes3.simulator import Simulator
        from bacpypes3.primitivedata import Real
        from bacpypes3.basetypes import (
            BinaryPV, EngineeringUnits, EventState, Reliability,
        )
        from bacpypes3.local.device import DeviceObject
        from bacpypes3.local.object import (
            AnalogInputObject, AnalogOutputObject,
            BinaryInputObject, BinaryOutputObject,
            AnalogValueObject, BinaryValueObject,
        )
    except ImportError as e:
        log.warning(f"bacpypes3 not available ({e}), running fallback HTTP simulation")
        _run_fallback_bacnet(host)
        return

    class HVACController(DeviceObject):
        """Main HVAC BACnet controller with multiple objects."""

        def __init__(self):
            super().__init__(
                objectIdentifier=("device", 1001),
                objectName="HVAC-Controller-01",
                vendorName="OT-Lab-Sim",
                modelName="BACnet-Sim v1.0",
                firmwareRevision="2.1.3",
                applicationSoftwareVersion="3.0.0",
                location="Building-A-Floor-2",
                description="Main HVAC BACnet controller",
                apduSegmentTimeout=6000,
                apduTimeout=6000,
                maxApduLengthAccepted=1476,
                segmentationSupported="segmentedBoth",
                numberOfApduRetries=3,
                deviceAddressBinding=[],
                activeCovSubscriptions=[],
            )

            # Temperature sensors (Analog Inputs)
            self.add_object(AnalogInputObject(
                objectIdentifier=("analogInput", 0),
                objectName="Supply-Air-Temp",
                description="Supply air temperature sensor",
                presentValue=Real(18.5),
                units=EngineeringUnits("degreesCelsius"),
                reliability=Reliability("noFaultDetected"),
                eventState=EventState("normal"),
                outOfService=False,
                covIncrement=0.5,
            ))
            self.add_object(AnalogInputObject(
                objectIdentifier=("analogInput", 1),
                objectName="Return-Air-Temp",
                description="Return air temperature sensor",
                presentValue=Real(24.0),
                units=EngineeringUnits("degreesCelsius"),
                reliability=Reliability("noFaultDetected"),
                eventState=EventState("normal"),
            ))
            self.add_object(AnalogInputObject(
                objectIdentifier=("analogInput", 2),
                objectName="Outdoor-Air-Temp",
                description="Outside air temperature",
                presentValue=Real(32.0),
                units=EngineeringUnits("degreesCelsius"),
                reliability=Reliability("noFaultDetected"),
                eventState=EventState("normal"),
            ))
            self.add_object(AnalogInputObject(
                objectIdentifier=("analogInput", 3),
                objectName="Chilled-Water-Temp",
                description="Chilled water supply temperature",
                presentValue=Real(7.0),
                units=EngineeringUnits("degreesCelsius"),
                reliability=Reliability("noFaultDetected"),
            ))
            self.add_object(AnalogInputObject(
                objectIdentifier=("analogInput", 4),
                objectName="Hot-Water-Temp",
                description="Hot water supply temperature",
                presentValue=Real(65.0),
                units=EngineeringUnits("degreesCelsius"),
                reliability=Reliability("noFaultDetected"),
            ))

            # Pressure sensors (Analog Inputs)
            self.add_object(AnalogInputObject(
                objectIdentifier=("analogInput", 5),
                objectName="Duct-Static-Pressure",
                description="Duct static pressure sensor",
                presentValue=Real(250.0),
                units=EngineeringUnits("pascals"),
                reliability=Reliability("noFaultDetected"),
            ))

            # Controllable outputs (Analog Outputs)
            self.add_object(AnalogOutputObject(
                objectIdentifier=("analogOutput", 0),
                objectName="Damper-Position-CMD",
                description="VAV damper position command",
                presentValue=Real(65.0),
                units=EngineeringUnits("percent"),
                priorityArray=[None] * 16,
                relinquishDefault=Real(0.0),
            ))
            self.add_object(AnalogOutputObject(
                objectIdentifier=("analogOutput", 1),
                objectName="Fan-Speed-CMD",
                description="Supply fan speed command (Hz)",
                presentValue=Real(45.0),
                units=EngineeringUnits("hertz"),
                priorityArray=[None] * 16,
                relinquishDefault=Real(0.0),
            ))
            self.add_object(AnalogOutputObject(
                objectIdentifier=("analogOutput", 2),
                objectName="Valve-Position-CMD",
                description="Chilled water valve position",
                presentValue=Real(55.0),
                units=EngineeringUnits("percent"),
                priorityArray=[None] * 16,
                relinquishDefault=Real(0.0),
            ))

            # Binary inputs
            self.add_object(BinaryInputObject(
                objectIdentifier=("binaryInput", 0),
                objectName="Fan-Status",
                description="Supply fan running status",
                presentValue=BinaryPV("active"),
            ))
            self.add_object(BinaryInputObject(
                objectIdentifier=("binaryInput", 1),
                objectName="Filter-Dirty",
                description="Air filter dirty status",
                presentValue=BinaryPV("inactive"),
            ))
            self.add_object(BinaryInputObject(
                objectIdentifier=("binaryInput", 2),
                objectName="Fire-Alarm",
                description="Fire alarm system status",
                presentValue=BinaryPV("inactive"),
            ))

            # Binary outputs (controllable)
            self.add_object(BinaryOutputObject(
                objectIdentifier=("binaryOutput", 0),
                objectName="AHU-Start-Stop",
                description="AHU start/stop command",
                presentValue=BinaryPV("active"),
                priorityArray=[None] * 16,
                relinquishDefault=BinaryPV("inactive"),
            ))
            self.add_object(BinaryOutputObject(
                objectIdentifier=("binaryOutput", 1),
                objectName="Lighting-Zone-A",
                description="Lighting zone A control",
                presentValue=BinaryPV("inactive"),
                priorityArray=[None] * 16,
                relinquishDefault=BinaryPV("inactive"),
            ))

        def update(self):
            """Simulate process value changes."""
            import random as rnd
            for obj in self.object_list:
                if isinstance(obj, AnalogInputObject):
                    if "Temp" in obj.objectName:
                        drift = rnd.gauss(0, 0.3)
                        new_val = float(obj.presentValue) + drift
                        obj.presentValue = Real(max(-10, min(60, new_val)))
                    elif "Pressure" in obj.objectName:
                        drift = rnd.gauss(0, 2)
                        obj.presentValue = Real(max(0, float(obj.presentValue) + drift))

    try:
        sim = Simulator(host=host)
        device = HVACController()

        sim.add_device(device)
        log.info(f"BACnet simulator running on {host}:47808")

        def process_loop():
            while True:
                device.update()
                time.sleep(3)

        t = threading.Thread(target=process_loop, daemon=True)
        t.start()

        sim.run()
    except Exception as e:
        log.error(f"BACnet simulator error: {e}")
        _run_fallback_bacnet(host)


def _run_fallback_bacnet(host="0.0.0.0"):
    """Fallback BACnet-like simulation via HTTP API."""
    from flask import Flask, jsonify, request

    app = Flask("bacnet-fallback")
    objects = {
        "analogInput:0": {"name": "Supply-Air-Temp", "value": 18.5, "units": "°C"},
        "analogInput:1": {"name": "Return-Air-Temp", "value": 24.0, "units": "°C"},
        "analogInput:2": {"name": "Outdoor-Air-Temp", "value": 32.0, "units": "°C"},
        "analogInput:3": {"name": "Chilled-Water-Temp", "value": 7.0, "units": "°C"},
        "analogOutput:0": {"name": "Damper-Position", "value": 65.0, "units": "%"},
        "analogOutput:1": {"name": "Fan-Speed", "value": 45.0, "units": "Hz"},
        "binaryInput:0": {"name": "Fan-Status", "value": True},
        "binaryInput:1": {"name": "Filter-Dirty", "value": False},
        "binaryOutput:0": {"name": "AHU-Start-Stop", "value": True},
    }

    @app.route("/bacnet/whois")
    def whois():
        return jsonify({
            "devices": [
                {"id": 1001, "name": "HVAC-Controller-01", "vendor": "OT-Lab-Sim"}
            ]
        })

    @app.route("/bacnet/objects")
    def list_objects():
        results = []
        for oid, data in objects.items():
            results.append({"id": oid, **data})
        return jsonify(results)

    @app.route("/bacnet/read/<obj_type>/<int:instance>")
    def read(obj_type, instance):
        key = f"{obj_type}:{instance}"
        if key in objects:
            return jsonify(objects[key])
        return jsonify({"error": "not found"}), 404

    @app.route("/bacnet/write/<obj_type>/<int:instance>", methods=["POST"])
    def write(obj_type, instance):
        key = f"{obj_type}:{instance}"
        if key not in objects:
            return jsonify({"error": "not found"}), 404
        data = request.get_json()
        if "value" in data:
            objects[key]["value"] = data["value"]
            log.info(f"BACnet {key} written to {data['value']}")
            return jsonify({"status": "ok"})
        return jsonify({"error": "value required"}), 400

    def update_loop():
        import random as rnd
        while True:
            for key in objects:
                if "Temp" in objects[key]["name"]:
                    drift = rnd.gauss(0, 0.3)
                    objects[key]["value"] = round(max(-10, min(60, float(objects[key]["value"]) + drift)), 2)
            time.sleep(3)

    t = threading.Thread(target=update_loop, daemon=True)
    t.start()

    log.info(f"BACnet fallback HTTP simulator starting on {host}:8083")
    app.run(host=host, port=8083)
