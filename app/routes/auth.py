"""
Authentication routes for admin login/logout.
Includes CAPTCHA validation for login attempts.
"""
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import Admin, AdminLog, db, log_admin_action
from app.utils.captcha import get_captcha_question, validate_captcha

auth_bp = Blueprint('auth', __name__, url_prefix='/admin')


def login_required(f):
    """
    Decorator to require admin login for protected routes.
    Redirects to login page if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/')
def admin_index():
    """
    Redirect /admin to dashboard if logged in, otherwise to login.
    """
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Admin login page with CAPTCHA validation.
    """
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        captcha_input = request.form.get('captcha', '')
        
        # Validate CAPTCHA first (before any DB access)
        if not validate_captcha(captcha_input):
            flash('Incorrect answer. Please solve the math problem.', 'error')
            # Generate new CAPTCHA for retry
            captcha_question = get_captcha_question()
            return render_template('admin/login.html', captcha_question=captcha_question)
        
        # Validate credentials
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username
            session['admin_id'] = admin.id
            session['is_super_admin'] = admin.is_super_admin
            
            # Update last login
            admin.last_login = datetime.utcnow()
            
            # Log the action
            log_admin_action(
                admin_id=admin.id,
                action='login',
                details=f'Admin {admin.username} logged in',
                ip_address=request.remote_addr
            )
            db.session.commit()
            
            flash('Login successful!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            # Log failed attempt
            log_admin_action(
                admin_id=None,
                action='login_failed',
                details=f'Failed login attempt for username: {username}',
                ip_address=request.remote_addr
            )
            db.session.commit()
            flash('Invalid username or password.', 'error')
            # Generate new CAPTCHA for retry
            captcha_question = get_captcha_question()
            return render_template('admin/login.html', captcha_question=captcha_question)
    
    # GET request - generate new CAPTCHA
    captcha_question = get_captcha_question()
    return render_template('admin/login.html', captcha_question=captcha_question)


@auth_bp.route('/logout')
def logout():
    """
    Admin logout - clears session.
    """
    admin_id = session.get('admin_id')
    username = session.get('admin_username')
    
    if admin_id:
        log_admin_action(
            admin_id=admin_id,
            action='logout',
            details=f'Admin {username} logged out',
            ip_address=request.remote_addr
        )
        db.session.commit()
    
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    session.pop('admin_id', None)
    session.pop('is_super_admin', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
