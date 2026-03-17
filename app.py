import os
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
from extensions import db, login_manager

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///guild.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "admin_login"
login_manager.login_message = "Pro přístup do administrace se přihlaste."

from models import Admin, Event, EventCategory


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# ─────────────────────────────────────────────
# PUBLIC ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    categories = EventCategory.query.all()
    return render_template("calendar.html", categories=categories)

@app.route("/api/events")
def api_events():
    """Return events as JSON for FullCalendar."""
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    query = Event.query
    if start_str:
        start_dt = datetime.fromisoformat(start_str[:19])
        query = query.filter(Event.start_datetime >= start_dt)
    if end_str:
        end_dt = datetime.fromisoformat(end_str[:19])
        query = query.filter(Event.start_datetime <= end_dt)

    events = query.all()
    result = []

    for event in events:
        result.append(event.to_dict())

        # Generate recurring instances within range
        if event.is_recurring and event.recurrence_rule:
            result.extend(_generate_recurring(event, start_str, end_str))

    return jsonify(result)


def _generate_recurring(event, start_str, end_str):
    """Generate recurring event instances."""
    instances = []
    rule = event.recurrence_rule
    deltas = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1), "monthly": None}

    if rule not in deltas:
        return instances

    end_limit = (
        datetime.combine(event.recurrence_end, datetime.min.time())
        if event.recurrence_end
        else datetime.utcnow() + timedelta(days=365)
    )
    if end_str:
        end_limit = min(end_limit, datetime.fromisoformat(end_str[:19]))

    current_start = event.start_datetime
    duration = (
        (event.end_datetime - event.start_datetime)
        if event.end_datetime
        else timedelta(hours=1)
    )

    for _ in range(200):  # safety cap
        if rule == "monthly":
            month = current_start.month + 1
            year = current_start.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            try:
                current_start = current_start.replace(year=year, month=month)
            except ValueError:
                break
        else:
            current_start += deltas[rule]

        if current_start > end_limit:
            break

        inst = event.to_dict()
        inst["id"] = f"{event.id}_r_{current_start.date().isoformat()}"
        inst["start"] = current_start.isoformat()
        inst["end"] = (current_start + duration).isoformat()
        inst["extendedProps"]["isRecurringInstance"] = True
        instances.append(inst)

    return instances


# ─────────────────────────────────────────────
# ADMIN AUTH
# ─────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin, remember=request.form.get("remember") == "on")
            return redirect(url_for("admin_dashboard"))
        flash("Nesprávné přihlašovací údaje.", "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("index"))


# ─────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────

@app.route("/admin")
@login_required
def admin_dashboard():
    events = Event.query.order_by(Event.start_datetime.desc()).all()
    categories = EventCategory.query.all()
    return render_template("admin/dashboard.html", events=events, categories=categories)


# ─────────────────────────────────────────────
# ADMIN EVENTS CRUD
# ─────────────────────────────────────────────

@app.route("/admin/events/new", methods=["GET", "POST"])
@login_required
def admin_event_new():
    categories = EventCategory.query.all()
    if request.method == "POST":
        event = _event_from_form(request.form)
        db.session.add(event)
        db.session.commit()
        flash("Event byl přidán.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/event_form.html", event=None, categories=categories, action="Přidat event")


@app.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def admin_event_edit(event_id):
    event = Event.query.get_or_404(event_id)
    categories = EventCategory.query.all()
    if request.method == "POST":
        _update_event_from_form(event, request.form)
        db.session.commit()
        flash("Event byl upraven.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/event_form.html", event=event, categories=categories, action="Upravit event")


@app.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@login_required
def admin_event_delete(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event byl smazán.", "success")
    return redirect(url_for("admin_dashboard"))


def _event_from_form(form):
    event = Event()
    _update_event_from_form(event, form)
    return event


def _update_event_from_form(event, form):
    event.title = form.get("title", "").strip()
    event.description = form.get("description", "").strip()
    event.location = form.get("location", "").strip()
    event.all_day = form.get("all_day") == "on"

    start_str = form.get("start_datetime")
    end_str = form.get("end_datetime")
    event.start_datetime = datetime.fromisoformat(start_str) if start_str else datetime.utcnow()
    event.end_datetime = datetime.fromisoformat(end_str) if end_str else None

    cat_id = form.get("category_id")
    event.category_id = int(cat_id) if cat_id else None

    event.is_recurring = form.get("is_recurring") == "on"
    event.recurrence_rule = form.get("recurrence_rule") or None
    rec_end = form.get("recurrence_end")
    event.recurrence_end = date.fromisoformat(rec_end) if rec_end else None


# ─────────────────────────────────────────────
# ADMIN CATEGORIES CRUD
# ─────────────────────────────────────────────

@app.route("/admin/categories", methods=["GET", "POST"])
@login_required
def admin_categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        color = request.form.get("color", "#6C63FF")
        if name:
            cat = EventCategory(name=name, color=color)
            db.session.add(cat)
            db.session.commit()
            flash(f"Kategorie '{name}' přidána.", "success")
        return redirect(url_for("admin_categories"))

    categories = EventCategory.query.all()
    return render_template("admin/categories.html", categories=categories)


@app.route("/admin/categories/<int:cat_id>/delete", methods=["POST"])
@login_required
def admin_category_delete(cat_id):
    cat = EventCategory.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    flash("Kategorie smazána.", "success")
    return redirect(url_for("admin_categories"))


# ─────────────────────────────────────────────
# DB INIT + SEED
# ─────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin if none exists
        if not Admin.query.first():
            admin = Admin(username="admin")
            admin.set_password(os.environ.get("ADMIN_PASSWORD", "lunarlegion123"))
            db.session.add(admin)

        # Create default categories
        default_cats = [
            ("Raid", "#e74c3c"),
            ("PvP", "#e67e22"),
            ("Guild Meeting", "#9b59b6"),
            ("Dungeon", "#2980b9"),
            ("Ostatní", "#27ae60"),
        ]
        for name, color in default_cats:
            if not EventCategory.query.filter_by(name=name).first():
                db.session.add(EventCategory(name=name, color=color))

        db.session.commit()
        print("✅ Database initialized.")


# Inicializace DB při startu
with app.app_context():
    db.create_all()
    # seed admin + kategorie...

if __name__ == "__main__":
    app.run(debug=True)
