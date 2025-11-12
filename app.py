from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import db, Booking, Admin
import os
from datetime import datetime
from math import ceil

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# Database configuration (Render uses DATABASE_URL, local uses SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///admin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ---------------------------
# Authentication Routes
# ---------------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    """Admin login page"""
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

# ---------------------------
# Dashboard (Protected)
# ---------------------------

@app.route('/dashboard')
def dashboard():
    """View bookings with filters and pagination"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    status_filter = request.args.get('status')
    date_filter = request.args.get('date')
    page = int(request.args.get('page', 1))
    per_page = 5

    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if date_filter:
        query = query.filter_by(date=date_filter)

    total = query.count()
    total_pages = ceil(total / per_page)
    bookings = query.order_by(Booking.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return render_template('dashboard.html', bookings=bookings, total_pages=total_pages, current_page=page,
                           status_filter=status_filter, date_filter=date_filter)

@app.route('/update/<int:booking_id>/<string:new_status>')
def update_status(booking_id, new_status):
    """Update booking status"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    booking = Booking.query.get_or_404(booking_id)
    booking.status = new_status
    db.session.commit()
    return redirect(url_for('dashboard'))

# ---------------------------
# API Endpoints
# ---------------------------

@app.route('/api/bookings', methods=['GET'])
def api_get_bookings():
    """API endpoint to get bookings (for integration with services.com)"""
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return jsonify([
        {"id": b.id, "name": b.name, "service": b.service, "date": b.date, "status": b.status}
        for b in bookings
    ])

@app.route('/api/add_booking', methods=['POST'])
def api_add_booking():
    """API endpoint to add booking from main site"""
    data = request.get_json()
    booking = Booking(
        name=data['name'],
        service=data['service'],
        date=data.get('date', datetime.now().strftime('%Y-%m-%d')),
        status='Pending'
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({"message": "Booking added successfully"}), 201

# ---------------------------
# Auto-create DB
# ---------------------------
with app.app_context():
    db.create_all()
    # Create default admin if not present
    if not Admin.query.first():
        admin = Admin(username='admin', password='admin123')
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
