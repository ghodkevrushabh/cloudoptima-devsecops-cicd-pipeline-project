from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-enterprise-key-change-this-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ems.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirects here if unauthorized


# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'LOGIN' or 'LOGOUT'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('logs', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- AUTH ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        # Verify user exists AND password hash matches
        if user and check_password_hash(user.password_hash, password):
            login_user(user)

            # Create Audit Log for LOGIN
            log = AuditLog(user_id=user.id, action='LOGIN')
            db.session.add(log)
            db.session.commit()

            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    # Create Audit Log for LOGOUT before terminating session
    log = AuditLog(user_id=current_user.id, action='LOGOUT')
    db.session.add(log)
    db.session.commit()

    logout_user()
    return redirect(url_for('login'))


# --- MAIN APP ROUTES ---
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)


# --- ADMIN-ONLY: AUDIT LOG VIEW (RBAC) ---
@app.route('/audit-logs')
@login_required
def view_audit_logs():
    # Simple role check: only 'admin' username can view this page
    if current_user.username != 'admin':
        flash('Access denied: Admins only.')
        return redirect(url_for('dashboard'))

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('audit_logs.html', logs=logs)


# --- BOOTSTRAP DB + DEFAULT ADMIN ---
with app.app_context():
    db.create_all()
    # Create a default admin user if the database is empty
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin = User(username='admin', password_hash=hashed_pw)
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created: admin / admin123")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
