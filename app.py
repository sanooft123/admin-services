from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import db, Booking, Admin, User
import os
from datetime import datetime
from math import ceil

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Database
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///admin.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# ---------------------------
# AUTHENTICATION
# ---------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        admin = Admin.query.filter_by(username=username, password=password).first()
        if admin:
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("login"))

# ---------------------------
# DASHBOARD
# ---------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    status_filter = request.args.get("status")
    page = int(request.args.get("page", 1))
    per_page = 5

    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    total = query.count()
    total_pages = ceil(total / per_page)
    bookings = query.order_by(Booking.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "dashboard.html",
        bookings=bookings,
        total_pages=total_pages,
        current_page=page,
        status_filter=status_filter,
    )

@app.route("/update/<int:booking_id>/<string:new_status>")
def update_status(booking_id, new_status):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    booking = Booking.query.get_or_404(booking_id)
    booking.status = new_status
    db.session.commit()
    return redirect(url_for("dashboard"))

# ---------------------------
# USER MANAGEMENT
# ---------------------------
@app.route("/users")
def users():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    search = request.args.get("search", "")
    query = User.query

    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.phone.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    users = query.order_by(User.id.desc()).all()
    user_data = [
        {
            "id": u.id,
            "name": u.name,
            "phone": u.phone,
            "email": u.email,
            "created_at": u.created_at.strftime("%Y-%m-%d"),
            "is_blocked": u.is_blocked,
            "total_bookings": len(u.bookings),
        }
        for u in users
    ]
    return render_template("users.html", users=user_data, search=search)

@app.route("/users/<int:user_id>")
def user_details(user_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    user = User.query.get_or_404(user_id)
    bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.id.desc()).all()
    return render_template("user_details.html", user=user, bookings=bookings)

@app.route("/users/block/<int:user_id>")
def block_user(user_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    user = User.query.get_or_404(user_id)
    user.is_blocked = True
    db.session.commit()
    return redirect(url_for("users"))

@app.route("/users/unblock/<int:user_id>")
def unblock_user(user_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    user = User.query.get_or_404(user_id)
    user.is_blocked = False
    db.session.commit()
    return redirect(url_for("users"))

@app.route("/users/delete/<int:user_id>")
def delete_user(user_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("users"))

# ---------------------------
# API ENDPOINTS
# ---------------------------
@app.route("/api/bookings")
def api_get_bookings():
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return jsonify([
        {"id": b.id, "user_id": b.user_id, "service": b.service, "date": b.date, "status": b.status}
        for b in bookings
    ])

# ---------------------------
# INITIALIZE DB
# ---------------------------
with app.app_context():
    db.create_all()
    if not Admin.query.first():
        db.session.add(Admin(username="admin", password="admin123"))
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
