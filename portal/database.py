from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    avatar = db.Column(db.String(200), default="🎓")

    progress = db.relationship("UserProgress", backref="user", lazy="dynamic")
    achievements = db.relationship("UserAchievement", backref="user", lazy="dynamic")


class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(10), default="🏭")
    color = db.Column(db.String(7), default="#3498db")

    quests = db.relationship("Quest", backref="zone", lazy="dynamic")


class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("zone.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default="beginner")
    order = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=100)
    category = db.Column(db.String(50), default="detection")

    objectives = db.relationship("Objective", backref="quest", lazy="dynamic")


class Objective(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey("quest.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)
    hints = db.Column(db.Text, default="")
    validation_type = db.Column(db.String(50), default="manual")
    validation_data = db.Column(db.Text, default="")


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(10), default="🏆")
    criteria = db.Column(db.String(100), nullable=False)


class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey("quest.id"), nullable=False)
    objective_id = db.Column(db.Integer, db.ForeignKey("objective.id"), nullable=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    achievement_id = db.Column(
        db.Integer, db.ForeignKey("achievement.id"), nullable=False
    )
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class LabService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="stopped")
    endpoint = db.Column(db.String(200), default="")
    icon = db.Column(db.String(10), default="⚙️")
