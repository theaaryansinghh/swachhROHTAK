from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import time

app = Flask(__name__)
app.secret_key = 'A7sd92!jkdf*23jfF_5d@FdfhZ12sdf9832x'  # Replace with something secure

# === Upload folder ===
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === PostgreSQL DATABASE URI ===
# Replace with your actual PostgreSQL credentials or Render's URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://swachhrohtak_user:M7i0JrxveSPqVoULBWweUHnEVjIST54V@dpg-d1qai3ur433s73e5kpc0-a.oregon-postgres.render.com/swachhrohtak'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# === Admin password ===
ADMIN_PASSWORD = 'rohtak123'

# === Simple IP-based spam protection ===
last_submission_time = {}

# === Database model ===
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(300), nullable=False)
    comment = db.Column(db.Text)
    location = db.Column(db.String(100))
    photo = db.Column(db.String(300))
    time = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Unresolved')

# === Homepage ===
@app.route('/')
def index():
    return render_template('index.html')

# === Submit Report ===
@app.route('/submit', methods=['POST'])
def submit():
    ip = request.remote_addr
    now = time.time()
    if ip in last_submission_time and now - last_submission_time[ip] < 30:
        return "You're submitting too quickly. Please wait.", 429
    last_submission_time[ip] = now

    address = request.form['address']
    comment = request.form.get('comment', '')
    location = request.form.get('location', 'Not Provided')
    photo = request.files['photo']

    if photo:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{photo.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(filepath)

        new_report = Report(
            address=address,
            comment=comment,
            location=location,
            photo=filepath,
            time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            status='Unresolved'
        )
        db.session.add(new_report)
        db.session.commit()

    return redirect(url_for('reports_page'))

# === Public report view ===
@app.route('/reports')
def reports_page():
    reports = Report.query.order_by(Report.time.desc()).all()
    return render_template('reports.html', reports=reports)

# === Admin login + dashboard ===
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        return render_template('admin_login.html', error="Incorrect password")

    if not session.get('admin'):
        return render_template('admin_login.html')

    reports = Report.query.order_by(Report.time.desc()).all()
    total_reports = len(reports)
    cleaned = sum(1 for r in reports if r.status == 'Cleaned')
    unresolved = total_reports - cleaned

    return render_template('admin.html', reports=reports,
                           total_reports=total_reports,
                           cleaned=cleaned,
                           unresolved=unresolved)

# === Update report status ===
@app.route('/update-status/<int:report_id>', methods=['POST'])
def update_status(report_id):
    if not session.get('admin'):
        return redirect('/admin')
    new_status = request.form['status']
    report = Report.query.get_or_404(report_id)
    report.status = new_status
    db.session.commit()
    return redirect('/admin')

# === Delete report ===
@app.route('/delete/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    if not session.get('admin'):
        return redirect('/admin')
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return redirect('/admin')

# === Logout ===
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# === Run app ===
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
