from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Admin(UserMixin, db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class EventCategory(db.Model):
    __tablename__ = "event_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), nullable=False, default="#6C63FF")  # hex color
    events = db.relationship("Event", backref="category", lazy=True)


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    location = db.Column(db.String(200), default="")
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=True)
    all_day = db.Column(db.Boolean, default=False)
    category_id = db.Column(db.Integer, db.ForeignKey("event_categories.id"), nullable=True)

    # Recurrence
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_rule = db.Column(db.String(20), nullable=True)  # daily, weekly, monthly
    recurrence_end = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        color = self.category.color if self.category else "#4e9af1"
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start_datetime.isoformat(),
            "end": self.end_datetime.isoformat() if self.end_datetime else None,
            "allDay": self.all_day,
            "backgroundColor": color,
            "borderColor": color,
            "extendedProps": {
                "description": self.description,
                "location": self.location,
                "category": self.category.name if self.category else "Obecné",
                "isRecurring": self.is_recurring,
                "recurrenceRule": self.recurrence_rule,
            },
        }
