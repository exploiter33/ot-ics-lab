from datetime import datetime, timezone

import requests
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from config import Config
from database import (
    Achievement,
    LabService,
    Objective,
    Quest,
    User,
    UserAchievement,
    UserProgress,
    Zone,
    db,
)

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_now():
    return {"now": datetime.now(timezone.utc)}


def seed_database():
    if Zone.query.first():
        return

    zones_data = [
        {
            "level": 0,
            "name": "Physical Process",
            "description": "Sensors, actuators, and physical equipment. The front line of industrial operations.",
            "icon": "🔧",
            "color": "#2ecc71",
        },
        {
            "level": 1,
            "name": "Basic Control",
            "description": "PLCs, RTUs, and embedded controllers that directly interact with physical processes.",
            "icon": "⚡",
            "color": "#3498db",
        },
        {
            "level": 2,
            "name": "Supervisory Control",
            "description": "SCADA servers, HMIs, and engineering workstations that monitor and control Zone 1 devices.",
            "icon": "🖥️",
            "color": "#9b59b6",
        },
        {
            "level": 3,
            "name": "Operations Management",
            "description": "MES, historians, and domain controllers managing plant-wide operations.",
            "icon": "📊",
            "color": "#e67e22",
        },
        {
            "level": 4,
            "name": "Enterprise Systems",
            "description": "ERP, databases, and business systems that interface with OT environments.",
            "icon": "🏢",
            "color": "#e74c3c",
        },
        {
            "level": 5,
            "name": "IT-OT DMZ",
            "description": "The critical boundary between IT and OT networks. Firewalls, jump boxes, and proxies.",
            "icon": "🛡️",
            "color": "#f1c40f",
        },
    ]

    for z in zones_data:
        db.session.add(Zone(**z))
    db.session.commit()

    quests_data = [
        {
            "zone_id": 2,
            "title": "Modbus Reconnaissance",
            "description": "Scan and enumerate Modbus devices on the network. Identify function codes and register values.",
            "difficulty": "beginner",
            "order": 1,
            "points": 100,
            "category": "reconnaissance",
            "objectives": [
                {
                    "title": "Discover Modbus Devices",
                    "description": "Use nmap or a Modbus scanner to find devices on port 5020. Identify at least 3 holding registers.",
                    "hints": "nmap -sV -p 5020 <target>",
                },
                {
                    "title": "Read Coil Values",
                    "description": "Read the state of coils 0-15 from the Modbus simulator. Identify which coils control the pump and valve.",
                    "hints": "Use mbpoll or modbus-cli to read coils.",
                },
                {
                    "title": "Identify Suspicious Register Changes",
                    "description": "Monitor register values over 60 seconds. Note any registers that change unexpectedly.",
                    "hints": "Poll holding registers every 5 seconds and log changes.",
                },
            ],
        },
        {
            "zone_id": 2,
            "title": "BACnet Object Enumeration",
            "description": "Enumerate BACnet devices and objects across the simulated building automation network.",
            "difficulty": "beginner",
            "order": 2,
            "points": 100,
            "category": "reconnaissance",
            "objectives": [
                {
                    "title": "BACnet Who-Is Discovery",
                    "description": "Send a Who-Is broadcast and identify all BACnet devices that respond.",
                    "hints": "bacnet Who-Is | bacwi",
                },
                {
                    "title": "Read Analog Inputs",
                    "description": "Read analog input values from the HVAC controller. Compare temperature and pressure readings.",
                    "hints": "bacrp <device> <type> <instance>",
                },
                {
                    "title": "Detect BACnet Anomalies",
                    "description": "Identify any BACnet objects with unexpected values or status flags set.",
                    "hints": "Look for objects in 'fault' or 'overridden' state.",
                },
            ],
        },
        {
            "zone_id": 3,
            "title": "SCADA Traffic Analysis",
            "description": "Capture and analyze SCADA network traffic to understand normal vs malicious patterns.",
            "difficulty": "intermediate",
            "order": 3,
            "points": 200,
            "category": "detection",
            "objectives": [
                {
                    "title": "Packet Capture",
                    "description": "Use tcpdump or Wireshark to capture Modbus traffic on the lab network.",
                    "hints": "tcpdump -i any port 5020 -w modbus_traffic.pcap",
                },
                {
                    "title": "Identify Normal Baselines",
                    "description": "Establish a baseline of normal register read/write operations during steady-state.",
                    "hints": "Analyze function code distribution and register access patterns.",
                },
                {
                    "title": "Detect Malicious Writes",
                    "description": "Identify write operations (FC=5,6,15,16) that change register values outside normal ranges.",
                    "hints": "Writes to holding registers that set values above safe thresholds are suspicious.",
                },
            ],
        },
        {
            "zone_id": 2,
            "title": "MQTT Protocol Exploitation",
            "description": "Explore MQTT topics, identify weak configurations, and detect unauthorized publishing.",
            "difficulty": "intermediate",
            "order": 4,
            "points": 200,
            "category": "detection",
            "objectives": [
                {
                    "title": "Subscribe to All Topics",
                    "description": "Subscribe to the wildcard '#' topic and enumerate all MQTT topics in use.",
                    "hints": "mosquitto_sub -h <host> -t '#' -v",
                },
                {
                    "title": "Identify Sensitive Topics",
                    "description": "Find topics publishing sensitive control commands or telemetry data.",
                    "hints": "Look for topics containing 'cmd', 'set', 'control', or 'alarm'.",
                },
                {
                    "title": "Detect Unauthorized Publishing",
                    "description": "Monitor for unexpected messages published to command topics.",
                    "hints": "The attack engine will occasionally publish malicious commands.",
                },
            ],
        },
        {
            "zone_id": 3,
            "title": "OPC UA Discovery & Security",
            "description": "Discover OPC UA servers, endpoints, and evaluate security configurations.",
            "difficulty": "intermediate",
            "order": 5,
            "points": 200,
            "category": "reconnaissance",
            "objectives": [
                {
                    "title": "Find OPC UA Endpoints",
                    "description": "Discover all OPC UA server endpoints and their security policies.",
                    "hints": "Use opcua-client or uaexpert to browse the server.",
                },
                {
                    "title": "Read Tag Values",
                    "description": "Connect and read variable values from the OPC UA server namespace.",
                    "hints": "Browse the Objects folder to find process variables.",
                },
                {
                    "title": "Check Security Settings",
                    "description": "Evaluate which endpoints allow unauthenticated or unencrypted access.",
                    "hints": "Check SecurityPolicy 'None' endpoints - these allow anonymous access.",
                },
            ],
        },
        {
            "zone_id": 1,
            "title": "Physical Process Anomaly Detection",
            "description": "Monitor simulated physical processes and detect anomalies caused by cyber attacks.",
            "difficulty": "advanced",
            "order": 6,
            "points": 300,
            "category": "detection",
            "objectives": [
                {
                    "title": "Establish Process Baseline",
                    "description": "Monitor temperature, pressure, and flow sensors for 5 minutes to establish normal ranges.",
                    "hints": "Collect data from Modbus and OPC UA and plot trends.",
                },
                {
                    "title": "Detect Process Anomalies",
                    "description": "Identify when sensor values deviate from normal operating ranges.",
                    "hints": "Look for sudden spikes, flatlines, or values outside 3 standard deviations.",
                },
                {
                    "title": "Identify Attack Signature",
                    "description": "Classify the anomaly as a fault or cyber attack based on the pattern of change.",
                    "hints": "Attacks often affect multiple related sensors simultaneously; faults are typically isolated.",
                },
            ],
        },
        {
            "zone_id": 6,
            "title": "IT-OT DMZ Monitoring",
            "description": "Monitor the boundary between IT and OT networks for intrusion attempts.",
            "difficulty": "advanced",
            "order": 7,
            "points": 300,
            "category": "detection",
            "objectives": [
                {
                    "title": "Analyze DMZ Firewall Logs",
                    "description": "Review simulated firewall logs to identify denied connection attempts.",
                    "hints": "Search Kibana for firewall deny events.",
                },
                {
                    "title": "Detect Lateral Movement",
                    "description": "Identify connection patterns suggesting an attacker moving from IT to OT zones.",
                    "hints": "Look for scanning activity originating from unexpected IP ranges.",
                },
                {
                    "title": "Correlate Events Across Zones",
                    "description": "Connect events from enterprise, DMZ, and control zones to reconstruct an attack chain.",
                    "hints": "Use Kibana to search across all indices with a time range.",
                },
            ],
        },
        {
            "zone_id": 2,
            "title": "S7 Protocol Deep Dive",
            "description": "Explore Siemens S7 communication, read/write data blocks, and detect manipulation.",
            "difficulty": "advanced",
            "order": 8,
            "points": 300,
            "category": "detection",
            "objectives": [
                {
                    "title": "S7 Device Discovery",
                    "description": "Discover S7 devices and identify their rack/slot configurations.",
                    "hints": "Use snap7-cli or python-snap7 to enumerate devices.",
                },
                {
                    "title": "Read Data Blocks",
                    "description": "Read DB1, DB2, and DB3 from the S7 simulator. Identify process values.",
                    "hints": "Each data block contains different categories of process data.",
                },
                {
                    "title": "Detect Block Manipulation",
                    "description": "Monitor for unauthorized writes to S7 data blocks during attack scenarios.",
                    "hints": "The attack engine may write malicious values to process data blocks.",
                },
            ],
        },
    ]

    for q_data in quests_data:
        objectives = q_data.pop("objectives")
        quest = Quest(**q_data)
        db.session.add(quest)
        db.session.flush()
        for i, obj_data in enumerate(objectives):
            db.session.add(Objective(quest_id=quest.id, order=i, **obj_data))
    db.session.commit()

    achievements_data = [
        {
            "title": "First Contact",
            "description": "Complete your first OT protocol reconnaissance quest",
            "icon": "🔰",
            "criteria": "complete_any_quest",
        },
        {
            "title": "Protocol Explorer",
            "description": "Enumerate devices across 3 different OT protocols",
            "icon": "🌐",
            "criteria": "complete_3_protocols",
        },
        {
            "title": "Traffic Analyst",
            "description": "Capture and analyze OT network traffic with Wireshark",
            "icon": "📡",
            "criteria": "complete_traffic_analysis",
        },
        {
            "title": "Threat Hunter",
            "description": "Detect an active attack scenario in the lab",
            "icon": "🔍",
            "criteria": "detect_attack",
        },
        {
            "title": "Process Guardian",
            "description": "Identify and classify 5 process anomalies",
            "icon": "🛡️",
            "criteria": "identify_5_anomalies",
        },
        {
            "title": "SIEM Master",
            "description": "Create a Kibana dashboard correlating OT events",
            "icon": "📊",
            "criteria": "create_kibana_dashboard",
        },
        {
            "title": "Purdumium",
            "description": "Complete quests in all 6 Purdue levels",
            "icon": "🏭",
            "criteria": "all_purdue_levels",
        },
        {
            "title": "OT Defender",
            "description": "Complete all quests in the lab",
            "icon": "🏆",
            "criteria": "all_quests_complete",
        },
    ]

    for a in achievements_data:
        db.session.add(Achievement(**a))
    db.session.commit()

    services_data = [
        {
            "name": "Protocol Simulators",
            "description": "Modbus, BACnet, OPC UA, MQTT, S7, Ethernet/IP simulators",
            "endpoint": "simulators:9099",
            "icon": "⚙️",
        },
        {
            "name": "MQTT Broker",
            "description": "Eclipse Mosquitto message broker for OT telemetry",
            "endpoint": "mosquitto:1883",
            "icon": "📨",
        },
        {
            "name": "Elasticsearch",
            "description": "SIEM search and analytics engine",
            "endpoint": "elasticsearch:9200",
            "icon": "🔎",
        },
        {
            "name": "Kibana",
            "description": "SIEM visualization and dashboarding",
            "endpoint": "kibana:5601",
            "icon": "📊",
        },
        {
            "name": "Logstash",
            "description": "Log ingestion and parsing pipeline",
            "endpoint": "logstash:5000",
            "icon": "📋",
        },
        {
            "name": "Attack Engine",
            "description": "Simulated attack scenario generator (no web interface)",
            "endpoint": "N/A (profile: attacks)",
            "icon": "⚔️",
        },
        {
            "name": "Safe Practice",
            "description": "Isolated protocol exploration sandbox",
            "endpoint": "safe-practice:9090",
            "icon": "🧪",
        },
    ]

    for s in services_data:
        db.session.add(LabService(**s))
    db.session.commit()


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            flash("Please enter a username.")
            return render_template("login.html")

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                display_name=username,
            )
            db.session.add(user)
            db.session.commit()
            flash(f"Welcome to the lab, {username}!")

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    zones = Zone.query.order_by(Zone.level).all()
    total_quests = Quest.query.count()
    completed_quests = (
        UserProgress.query.filter(
            UserProgress.user_id == current_user.id,
            UserProgress.completed == True,
            UserProgress.objective_id == None,
        )
        .distinct(UserProgress.quest_id)
        .count()
    )

    total_achievements = Achievement.query.count()
    earned_achievements = UserAchievement.query.filter_by(
        user_id=current_user.id
    ).count()

    services = LabService.query.all()

    recent_activity = (
        UserProgress.query.filter_by(user_id=current_user.id)
        .order_by(UserProgress.completed_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        zones=zones,
        total_quests=total_quests,
        completed_quests=completed_quests,
        total_achievements=total_achievements,
        earned_achievements=earned_achievements,
        services=services,
        recent_activity=recent_activity,
    )


@app.route("/zones")
@login_required
def zones():
    zones_list = Zone.query.order_by(Zone.level).all()
    zone_data = []
    for zone in zones_list:
        quests_in_zone = Quest.query.filter_by(zone_id=zone.id).count()
        completed_in_zone = (
            UserProgress.query.join(Quest)
            .filter(
                UserProgress.user_id == current_user.id,
                UserProgress.completed == True,
                UserProgress.objective_id == None,
                Quest.zone_id == zone.id,
            )
            .distinct(UserProgress.quest_id)
            .count()
        )
        zone_data.append(
            {
                "zone": zone,
                "total": quests_in_zone,
                "completed": completed_in_zone,
            }
        )
    return render_template("zones.html", zone_data=zone_data)


@app.route("/quests")
@login_required
def quests():
    zone_filter = request.args.get("zone", type=int)
    difficulty_filter = request.args.get("difficulty")

    query = Quest.query
    if zone_filter:
        query = query.filter_by(zone_id=zone_filter)
    if difficulty_filter:
        query = query.filter_by(difficulty=difficulty_filter)

    quests_list = query.order_by(Quest.zone_id, Quest.order).all()
    zones_list = Zone.query.order_by(Zone.level).all()

    quest_data = []
    for quest in quests_list:
        objectives = Objective.query.filter_by(quest_id=quest.id).order_by(
            Objective.order
        ).all()
        completed_count = UserProgress.query.filter(
            UserProgress.user_id == current_user.id,
            UserProgress.quest_id == quest.id,
            UserProgress.completed == True,
        ).count()
        quest_data.append(
            {
                "quest": quest,
                "objectives": objectives,
                "completed_count": completed_count,
                "total_objectives": len(objectives),
                "zone": Zone.query.get(quest.zone_id),
            }
        )

    return render_template(
        "quests.html",
        quest_data=quest_data,
        zones=zones_list,
        current_zone=zone_filter,
        current_difficulty=difficulty_filter,
    )


@app.route("/quest/<int:quest_id>")
@login_required
def quest_detail(quest_id):
    quest = db.session.get(Quest, quest_id)
    if not quest:
        flash("Quest not found.")
        return redirect(url_for("quests"))

    objectives = (
        Objective.query.filter_by(quest_id=quest.id)
        .order_by(Objective.order)
        .all()
    )
    zone = db.session.get(Zone, quest.zone_id)

    objective_progress = {}
    for obj in objectives:
        progress = UserProgress.query.filter_by(
            user_id=current_user.id,
            quest_id=quest.id,
            objective_id=obj.id,
        ).first()
        objective_progress[obj.id] = progress

    quest_complete = UserProgress.query.filter_by(
        user_id=current_user.id,
        quest_id=quest.id,
        objective_id=None,
        completed=True,
    ).first() is not None

    return render_template(
        "quest_detail.html",
        quest=quest,
        objectives=objectives,
        zone=zone,
        objective_progress=objective_progress,
        quest_complete=quest_complete,
    )


@app.route("/api/quest/<int:quest_id>/objective/<int:objective_id>/complete", methods=["POST"])
@login_required
def complete_objective(quest_id, objective_id):
    objective = db.session.get(Objective, objective_id)
    if not objective or objective.quest_id != quest_id:
        return jsonify({"error": "Objective not found"}), 404

    existing = UserProgress.query.filter_by(
        user_id=current_user.id,
        quest_id=quest_id,
        objective_id=objective_id,
    ).first()

    if not existing:
        existing = UserProgress(
            user_id=current_user.id,
            quest_id=quest_id,
            objective_id=objective_id,
            completed=True,
            completed_at=datetime.now(timezone.utc),
        )
        db.session.add(existing)
    else:
        existing.completed = True
        existing.completed_at = datetime.now(timezone.utc)

    all_objectives = Objective.query.filter_by(quest_id=quest_id).count()
    completed_objectives = (
        UserProgress.query.filter_by(
            user_id=current_user.id,
            quest_id=quest_id,
            completed=True,
        )
        .filter(UserProgress.objective_id.isnot(None))
        .count()
    )

    if completed_objectives >= all_objectives:
        quest_complete = UserProgress.query.filter_by(
            user_id=current_user.id,
            quest_id=quest_id,
            objective_id=None,
        ).first()
        if not quest_complete:
            db.session.add(
                UserProgress(
                    user_id=current_user.id,
                    quest_id=quest_id,
                    completed=True,
                    completed_at=datetime.now(timezone.utc),
                )
            )

    db.session.commit()

    # Check for achievements
    check_achievements(current_user.id)

    return jsonify(
        {
            "success": True,
            "objectives_completed": completed_objectives,
            "total_objectives": all_objectives,
        }
    )


def check_achievements(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return

    all_achievements = Achievement.query.all()
    for achievement in all_achievements:
        already_earned = UserAchievement.query.filter_by(
            user_id=user_id, achievement_id=achievement.id
        ).first()
        if already_earned:
            continue

        earned = False
        if achievement.criteria == "complete_any_quest":
            count = (
                UserProgress.query.filter_by(
                    user_id=user_id, completed=True, objective_id=None
                ).count()
            )
            earned = count >= 1

        elif achievement.criteria == "complete_3_protocols":
            count = (
                UserProgress.query.join(Quest)
                .filter(
                    UserProgress.user_id == user_id,
                    UserProgress.completed == True,
                    UserProgress.objective_id == None,
                )
                .distinct(Quest.category)
                .count()
            )
            earned = count >= 3

        elif achievement.criteria == "all_quests_complete":
            total = Quest.query.count()
            completed = (
                UserProgress.query.filter_by(
                    user_id=user_id, completed=True, objective_id=None
                ).count()
            )
            earned = completed >= total

        elif achievement.criteria == "all_purdue_levels":
            completed_zones = (
                db.session.query(Quest.zone_id)
                .join(UserProgress, Quest.id == UserProgress.quest_id)
                .filter(
                    UserProgress.user_id == user_id,
                    UserProgress.completed == True,
                    UserProgress.objective_id == None,
                )
                .distinct()
                .count()
            )
            earned = completed_zones >= 6

        if earned:
            db.session.add(
                UserAchievement(
                    user_id=user_id, achievement_id=achievement.id
                )
            )
    db.session.commit()


@app.route("/achievements")
@login_required
def achievements():
    all_achievements = Achievement.query.all()
    earned_ids = [
        a.achievement_id
        for a in UserAchievement.query.filter_by(user_id=current_user.id).all()
    ]
    achievement_data = []
    for a in all_achievements:
        achievement_data.append(
            {
                "achievement": a,
                "earned": a.id in earned_ids,
            }
        )
    return render_template("achievements.html", achievements=achievement_data)


@app.route("/guides")
@login_required
def guides():
    return render_template("guides.html")


@app.route("/services")
@login_required
def services():
    services_list = LabService.query.all()
    return render_template("services.html", services=services_list)


@app.route("/api/services/<int:service_id>/toggle", methods=["POST"])
@login_required
def toggle_service(service_id):
    service = db.session.get(LabService, service_id)
    if not service:
        return jsonify({"error": "Service not found"}), 404

    service.status = "running" if service.status == "stopped" else "stopped"
    db.session.commit()
    return jsonify({"status": service.status})


@app.route("/api/services/status", methods=["GET"])
@login_required
def service_status():
    services_list = LabService.query.all()
    return jsonify(
        {
            "services": [
                {"id": s.id, "name": s.name, "status": s.status}
                for s in services_list
            ]
        }
    )


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "ot-lab-portal"})


@app.route("/api/es-check")
@login_required
def es_check():
    try:
        resp = requests.get(
            f"{app.config['ELASTICSEARCH_URL']}/_cluster/health", timeout=5
        )
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e), "status": "unreachable"}), 503


# Initialize database on module load (runs under gunicorn too)
with app.app_context():
    db.create_all()
    seed_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
