from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from math import ceil
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# -------------------- DATABASE CONFIG --------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///admin.db').replace("postgres://", "postgresql://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -------------------- MODELS --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship("Booking", backref="user", lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    service_type = db.Column(db.String(100))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    location = db.Column(db.String(100))
    package = db.Column(db.String(50))
    addons = db.Column(db.String(200))
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

# -------------------- AUTH --------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username, password=password).first()
        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

# -------------------- DASHBOARD --------------------
@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    status_filter = request.args.get('status')
    page = int(request.args.get('page', 1))
    per_page = 10

    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    total = query.count()
    total_pages = ceil(total / per_page)
    bookings = query.order_by(Booking.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return render_template('dashboard.html', bookings=bookings, total_pages=total_pages, current_page=page)

@app.route('/update/<int:booking_id>/<string:new_status>')
def update_status(booking_id, new_status):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    booking = Booking.query.get_or_404(booking_id)
    booking.status = new_status
    db.session.commit()
    return redirect(url_for('dashboard'))

# -------------------- INITIAL SETUP --------------------
with app.app_context():
    db.create_all()
    if not Admin.query.first():
        admin = Admin(username='admin', password='admin123')
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
