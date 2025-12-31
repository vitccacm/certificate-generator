"""
Admin routes for dashboard, event management, and participant management.
All routes require admin authentication.
"""
import os
from datetime import datetime
import pandas as pd
from flask import (Blueprint, render_template, request, redirect, url_for, 
                   flash, current_app, session, Response, jsonify)
from werkzeug.utils import secure_filename
from app.models import db, Event, Participant, DownloadLog, Admin, AdminLog, log_admin_action
from app.routes.auth import login_required
from app.utils.helpers import (allowed_file, allowed_bulk_file, allowed_template_file,
                                secure_filename_custom, validate_email,
                                generate_unique_filename)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Admin dashboard with summary metrics.
    """
    total_events = Event.query.count()
    total_participants = Participant.query.count()
    total_downloads = db.session.query(db.func.sum(Participant.download_count)).scalar() or 0
    
    # All events for listing
    events = Event.query.order_by(Event.created_at.desc()).all()
    
    # Recent downloads
    recent_downloads = DownloadLog.query.order_by(
        DownloadLog.downloaded_at.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_events=total_events,
                         total_participants=total_participants,
                         total_downloads=total_downloads,
                         events=events,
                         recent_downloads=recent_downloads)


# ==================== ADMIN MANAGEMENT ====================

@admin_bp.route('/settings')
@login_required
def settings():
    """
    Admin settings page.
    """
    admins = Admin.query.order_by(Admin.created_at).all()
    return render_template('admin/settings.html', admins=admins)


@admin_bp.route('/settings/change-password', methods=['POST'])
@login_required
def change_password():
    """
    Change current admin's password.
    """
    admin_id = session.get('admin_id')
    admin = Admin.query.get_or_404(admin_id)
    
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not admin.check_password(current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('admin.settings'))
    
    if len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'error')
        return redirect(url_for('admin.settings'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('admin.settings'))
    
    admin.set_password(new_password)
    log_admin_action(
        admin_id=admin_id,
        action='change_password',
        details=f'Admin {admin.username} changed their password',
        ip_address=request.remote_addr
    )
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/admins/new', methods=['POST'])
@login_required
def new_admin():
    """
    Create a new admin account.
    """
    admin_id = session.get('admin_id')
    current_admin = Admin.query.get_or_404(admin_id)
    
    # Verify current admin's password
    password = request.form.get('admin_password', '')
    if not current_admin.check_password(password):
        flash('Your password is incorrect.', 'error')
        return redirect(url_for('admin.settings'))
    
    username = request.form.get('username', '').strip()
    new_password = request.form.get('new_password', '')
    is_super = request.form.get('is_super_admin') == 'on'
    
    if not username or not new_password:
        flash('Username and password are required.', 'error')
        return redirect(url_for('admin.settings'))
    
    if len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('admin.settings'))
    
    # Check if username exists
    if Admin.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('admin.settings'))
    
    new_admin = Admin(username=username, is_super_admin=is_super)
    new_admin.set_password(new_password)
    db.session.add(new_admin)
    
    log_admin_action(
        admin_id=admin_id,
        action='create_admin',
        details=f'Created new admin account: {username}',
        ip_address=request.remote_addr
    )
    db.session.commit()
    
    flash(f'Admin account "{username}" created successfully!', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/admins/<int:target_admin_id>/delete', methods=['POST'])
@login_required
def delete_admin(target_admin_id):
    """
    Delete an admin account (requires password verification).
    """
    admin_id = session.get('admin_id')
    current_admin = Admin.query.get_or_404(admin_id)
    target_admin = Admin.query.get_or_404(target_admin_id)
    
    # Can't delete yourself
    if admin_id == target_admin_id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.settings'))
    
    # Verify current admin's password
    password = request.form.get('admin_password', '')
    if not current_admin.check_password(password):
        flash('Your password is incorrect.', 'error')
        return redirect(url_for('admin.settings'))
    
    username = target_admin.username
    db.session.delete(target_admin)
    
    log_admin_action(
        admin_id=admin_id,
        action='delete_admin',
        details=f'Deleted admin account: {username}',
        ip_address=request.remote_addr
    )
    db.session.commit()
    
    flash(f'Admin account "{username}" deleted.', 'success')
    return redirect(url_for('admin.settings'))


# ==================== LOGS ====================

@admin_bp.route('/logs')
@login_required
def view_logs():
    """
    View admin activity logs.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    admin_logs = AdminLog.query.order_by(
        AdminLog.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/logs.html', logs=admin_logs, log_type='admin')


@admin_bp.route('/logs/downloads')
@login_required
def view_download_logs():
    """
    View user download logs.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    download_logs = DownloadLog.query.order_by(
        DownloadLog.downloaded_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/logs.html', logs=download_logs, log_type='downloads')


# ==================== EVENT MANAGEMENT ====================

@admin_bp.route('/events/new', methods=['GET', 'POST'])
@login_required
def new_event():
    """
    Create a new event.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        event_date_str = request.form.get('event_date', '').strip()
        is_visible = request.form.get('is_visible') == 'on'
        
        if not name:
            flash('Event name is required.', 'error')
            return render_template('admin/event_form.html', event=None)
        
        # Parse event date
        event_date = None
        if event_date_str:
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'error')
                return render_template('admin/event_form.html', event=None)
        
        event = Event(name=name, description=description, event_date=event_date, is_visible=is_visible)
        db.session.add(event)
        
        log_admin_action(
            admin_id=session.get('admin_id'),
            action='create_event',
            details=f'Created event: {name}',
            ip_address=request.remote_addr
        )
        db.session.commit()
        
        flash(f'Event "{name}" created successfully!', 'success')
        return redirect(url_for('admin.event_detail', event_id=event.id))
    
    return render_template('admin/event_form.html', event=None)


@admin_bp.route('/events/<int:event_id>')
@login_required
def event_detail(event_id):
    """
    Event detail page with all management options.
    """
    event = Event.query.get_or_404(event_id)
    participants = event.participants.order_by(Participant.name).all()
    return render_template('admin/event_detail.html', event=event, participants=participants)


@admin_bp.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    """
    Edit an existing event.
    """
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        event_date_str = request.form.get('event_date', '').strip()
        is_visible = request.form.get('is_visible') == 'on'
        
        if not name:
            flash('Event name is required.', 'error')
            return render_template('admin/event_form.html', event=event)
        
        # Parse event date
        event_date = None
        if event_date_str:
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'error')
                return render_template('admin/event_form.html', event=event)
        
        event.name = name
        event.description = description
        event.event_date = event_date
        event.is_visible = is_visible
        
        log_admin_action(
            admin_id=session.get('admin_id'),
            action='edit_event',
            details=f'Edited event: {name} (ID: {event_id})',
            ip_address=request.remote_addr
        )
        db.session.commit()
        
        flash(f'Event "{name}" updated successfully!', 'success')
        return redirect(url_for('admin.event_detail', event_id=event.id))
    
    return render_template('admin/event_form.html', event=event)


@admin_bp.route('/events/<int:event_id>/toggle', methods=['POST'])
@login_required
def toggle_event(event_id):
    """
    Toggle event visibility.
    """
    event = Event.query.get_or_404(event_id)
    event.is_visible = not event.is_visible
    
    status = 'visible' if event.is_visible else 'hidden'
    log_admin_action(
        admin_id=session.get('admin_id'),
        action='toggle_event_visibility',
        details=f'Set event "{event.name}" to {status}',
        ip_address=request.remote_addr
    )
    db.session.commit()
    
    flash(f'Event "{event.name}" is now {status}.', 'success')
    return redirect(url_for('admin.event_detail', event_id=event.id))


@admin_bp.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    """
    Delete an event and all associated participants (requires password verification).
    """
    event = Event.query.get_or_404(event_id)
    admin_id = session.get('admin_id')
    admin = Admin.query.get_or_404(admin_id)
    
    # Verify admin password
    password = request.form.get('admin_password', '')
    if not admin.check_password(password):
        flash('Incorrect password. Event was not deleted.', 'error')
        return redirect(url_for('admin.event_detail', event_id=event_id))
    
    event_name = event.name
    participant_count = event.participant_count
    
    # Delete associated certificate files
    for participant in event.participants:
        if participant.certificate_filename:
            cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], 
                                     participant.certificate_filename)
            if os.path.exists(cert_path):
                try:
                    os.remove(cert_path)
                except OSError:
                    pass  # Continue even if file deletion fails
    
    db.session.delete(event)
    
    log_admin_action(
        admin_id=admin_id,
        action='delete_event',
        details=f'Deleted event: {event_name} (had {participant_count} participants)',
        ip_address=request.remote_addr
    )
    db.session.commit()
    
    flash(f'Event "{event_name}" and all associated data deleted.', 'success')
    return redirect(url_for('admin.dashboard'))


# ==================== IMAGE UPLOAD (Multiple) ====================

@admin_bp.route('/events/<int:event_id>/upload-pdfs', methods=['POST'])
@login_required
def upload_pdfs(event_id):
    """
    Upload multiple PNG certificates to the certificates folder.
    """
    event = Event.query.get_or_404(event_id)
    
    if 'pdfs' not in request.files:
        flash('No files selected.', 'error')
        return redirect(url_for('admin.event_detail', event_id=event_id))
    
    files = request.files.getlist('pdfs')
    uploaded_count = 0
    errors = []
    
    for file in files:
        if file.filename == '':
            continue
        
        if not allowed_file(file.filename):
            errors.append(f'{file.filename}: Not a PNG file')
            continue
        
        # Save with secure filename
        filename = secure_filename(file.filename)
        cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], filename)
        
        # Handle duplicate filenames
        if os.path.exists(cert_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(cert_path):
                filename = f"{base}_{counter}{ext}"
                cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], filename)
                counter += 1
        
        file.save(cert_path)
        uploaded_count += 1
    
    if uploaded_count > 0:
        log_admin_action(
            admin_id=session.get('admin_id'),
            action='upload_pdfs',
            details=f'Uploaded {uploaded_count} PDF(s) for event: {event.name}',
            ip_address=request.remote_addr
        )
        db.session.commit()
        flash(f'Successfully uploaded {uploaded_count} image file(s).', 'success')
    
    if errors:
        for error in errors[:5]:  # Show max 5 errors
            flash(error, 'error')
    
    return redirect(url_for('admin.event_detail', event_id=event_id))


# ==================== PARTICIPANT MANAGEMENT ====================

@admin_bp.route('/events/<int:event_id>/participants/new', methods=['GET', 'POST'])
@login_required
def new_participant(event_id):
    """
    Add a new participant.
    Supports two modes:
    - 'pool': Add to certificate pool (uses template, no certificate upload)
    - 'custom': Upload custom certificate PNG
    """
    event = Event.query.get_or_404(event_id)
    mode = request.args.get('mode', 'pool')  # Default to pool mode
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        mode = request.form.get('mode', 'pool')
        
        # Validate inputs
        if not name or not email:
            flash('Name and email are required.', 'error')
            return render_template('admin/participant_form.html', event=event, participant=None, mode=mode)
        
        if not validate_email(email):
            flash('Invalid email format.', 'error')
            return render_template('admin/participant_form.html', event=event, participant=None, mode=mode)
        
        # Check for duplicate
        existing = Participant.query.filter_by(event_id=event_id, email=email).first()
        if existing:
            flash('A participant with this email already exists for this event.', 'error')
            return render_template('admin/participant_form.html', event=event, participant=None, mode=mode)
        
        certificate_filename = None
        
        if mode == 'custom':
            # Custom mode: require certificate file upload
            if 'certificate' not in request.files:
                flash('Certificate file is required for custom certificates.', 'error')
                return render_template('admin/participant_form.html', event=event, participant=None, mode=mode)
            
            file = request.files['certificate']
            if file.filename == '':
                flash('No file selected.', 'error')
                return render_template('admin/participant_form.html', event=event, participant=None, mode=mode)
            
            if not allowed_file(file.filename):
                flash('Only PNG files are allowed.', 'error')
                return render_template('admin/participant_form.html', event=event, participant=None, mode=mode)
            
            # Save certificate file
            filename = generate_unique_filename(file.filename, prefix=secure_filename_custom(name))
            cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], filename)
            file.save(cert_path)
            certificate_filename = filename
        # else: pool mode - certificate_filename remains None (will use template)
        
        # Create participant record
        participant = Participant(
            event_id=event_id,
            name=name,
            email=email,
            certificate_filename=certificate_filename
        )
        db.session.add(participant)
        
        log_admin_action(
            admin_id=session.get('admin_id'),
            action='add_participant',
            details=f'Added participant: {name} ({email}) to event: {event.name} (mode: {mode})',
            ip_address=request.remote_addr
        )
        db.session.commit()
        
        flash(f'Participant "{name}" added successfully!', 'success')
        return redirect(url_for('admin.event_detail', event_id=event_id))
    
    return render_template('admin/participant_form.html', event=event, participant=None, mode=mode)


@admin_bp.route('/participants/<int:participant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_participant(participant_id):
    """
    Edit a participant's details.
    """
    participant = Participant.query.get_or_404(participant_id)
    event = participant.event
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        if not name or not email:
            flash('Name and email are required.', 'error')
            return render_template('admin/participant_form.html', event=event, participant=participant)
        
        if not validate_email(email):
            flash('Invalid email format.', 'error')
            return render_template('admin/participant_form.html', event=event, participant=participant)
        
        # Check for duplicate (if email changed)
        if email != participant.email:
            existing = Participant.query.filter_by(
                event_id=participant.event_id, email=email
            ).first()
            if existing:
                flash('A participant with this email already exists for this event.', 'error')
                return render_template('admin/participant_form.html', event=event, participant=participant)
        
        # Handle new certificate file (optional)
        if 'certificate' in request.files:
            file = request.files['certificate']
            if file.filename != '':
                if not allowed_file(file.filename):
                    flash('Only PNG files are allowed.', 'error')
                    return render_template('admin/participant_form.html', event=event, participant=participant)
                
                # Delete old file
                old_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], 
                                       participant.certificate_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
                
                # Save new file
                filename = generate_unique_filename(file.filename, 
                                                   prefix=secure_filename_custom(name))
                cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], filename)
                file.save(cert_path)
                participant.certificate_filename = filename
        
        participant.name = name
        participant.email = email
        
        log_admin_action(
            admin_id=session.get('admin_id'),
            action='edit_participant',
            details=f'Edited participant: {name} ({email})',
            ip_address=request.remote_addr
        )
        db.session.commit()
        
        flash(f'Participant "{name}" updated successfully!', 'success')
        return redirect(url_for('admin.event_detail', event_id=participant.event_id))
    
    return render_template('admin/participant_form.html', event=event, participant=participant)


@admin_bp.route('/participants/<int:participant_id>/delete', methods=['POST'])
@login_required
def delete_participant(participant_id):
    """
    Delete a participant and their certificate (if custom).
    """
    participant = Participant.query.get_or_404(participant_id)
    event_id = participant.event_id
    name = participant.name
    email = participant.email
    
    # Delete certificate file only if it's a custom certificate
    if participant.certificate_filename:
        cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], 
                                participant.certificate_filename)
        if os.path.exists(cert_path):
            os.remove(cert_path)
    
    db.session.delete(participant)
    
    log_admin_action(
        admin_id=session.get('admin_id'),
        action='delete_participant',
        details=f'Deleted participant: {name} ({email})',
        ip_address=request.remote_addr
    )
    db.session.commit()
    
    flash(f'Participant "{name}" deleted.', 'success')
    return redirect(url_for('admin.event_detail', event_id=event_id))


# ==================== BULK UPLOAD ====================

@admin_bp.route('/events/<int:event_id>/bulk-upload', methods=['GET', 'POST'])
@login_required
def bulk_upload(event_id):
    """
    Bulk upload participants via CSV/Excel file.
    Shows preview before confirming import.
    """
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return render_template('admin/bulk_upload.html', event=event)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return render_template('admin/bulk_upload.html', event=event)
        
        if not allowed_bulk_file(file.filename):
            flash('Only CSV and Excel files are allowed.', 'error')
            return render_template('admin/bulk_upload.html', event=event)
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        
        try:
            # Parse file
            if filename.endswith('.csv'):
                df = pd.read_csv(upload_path)
            else:
                df = pd.read_excel(upload_path)
            
            # Validate required columns - always just name and email
            # Bulk upload always adds to the pool (template-based)
            required_columns = ['name', 'email']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                os.remove(upload_path)
                flash(f'Missing required columns: {", ".join(missing_columns)}', 'error')
                return render_template('admin/bulk_upload.html', event=event)
            
            # Validate data
            preview_data = []
            
            for idx, row in df.iterrows():
                name = str(row['name']).strip() if pd.notna(row['name']) else ''
                email = str(row['email']).strip().lower() if pd.notna(row['email']) else ''
                
                errors = []
                
                if not name:
                    errors.append('Missing name')
                if not email:
                    errors.append('Missing email')
                elif not validate_email(email):
                    errors.append('Invalid email')
                
                # Check for duplicate
                existing = Participant.query.filter_by(event_id=event_id, email=email).first()
                if existing:
                    errors.append('Duplicate email')
                
                preview_data.append({
                    'row': idx + 1,
                    'name': name,
                    'email': email,
                    'certificate_filename': '(Template)',
                    'valid': len(errors) == 0,
                    'errors': ', '.join(errors) if errors else None
                })
            
            # Store in session for confirmation
            session['bulk_upload_data'] = preview_data
            session['bulk_upload_event_id'] = event_id
            session['bulk_upload_file'] = upload_path
            
            return render_template('admin/bulk_upload_preview.html',
                                 event=event,
                                 preview_data=preview_data,
                                 valid_count=sum(1 for d in preview_data if d['valid']),
                                 invalid_count=sum(1 for d in preview_data if not d['valid']))
            
        except Exception as e:
            if os.path.exists(upload_path):
                os.remove(upload_path)
            flash(f'Error parsing file: {str(e)}', 'error')
            return render_template('admin/bulk_upload.html', event=event)
    
    return render_template('admin/bulk_upload.html', event=event)


@admin_bp.route('/bulk-upload/confirm', methods=['POST'])
@login_required
def bulk_upload_confirm():
    """
    Confirm and process bulk upload.
    """
    preview_data = session.get('bulk_upload_data', [])
    event_id = session.get('bulk_upload_event_id')
    upload_path = session.get('bulk_upload_file')
    
    if not preview_data or not event_id:
        flash('No upload data found. Please try again.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    event = Event.query.get(event_id)
    
    # Import valid records only
    imported_count = 0
    for record in preview_data:
        if record['valid']:
            # For template-based events, certificate_filename should be None
            cert_filename = record['certificate_filename']
            if cert_filename == '(Template)':
                cert_filename = None
            
            participant = Participant(
                event_id=event_id,
                name=record['name'],
                email=record['email'],
                certificate_filename=cert_filename
            )
            db.session.add(participant)
            imported_count += 1
    
    log_admin_action(
        admin_id=session.get('admin_id'),
        action='bulk_upload',
        details=f'Bulk imported {imported_count} participants to event: {event.name if event else event_id}',
        ip_address=request.remote_addr
    )
    db.session.commit()
    
    # Cleanup
    if upload_path and os.path.exists(upload_path):
        os.remove(upload_path)
    
    session.pop('bulk_upload_data', None)
    session.pop('bulk_upload_event_id', None)
    session.pop('bulk_upload_file', None)
    
    flash(f'Successfully imported {imported_count} participants.', 'success')
    return redirect(url_for('admin.event_detail', event_id=event_id))


@admin_bp.route('/bulk-upload/cancel', methods=['POST'])
@login_required
def bulk_upload_cancel():
    """
    Cancel bulk upload and cleanup.
    """
    upload_path = session.get('bulk_upload_file')
    event_id = session.get('bulk_upload_event_id')
    
    if upload_path and os.path.exists(upload_path):
        os.remove(upload_path)
    
    session.pop('bulk_upload_data', None)
    session.pop('bulk_upload_event_id', None)
    session.pop('bulk_upload_file', None)
    
    flash('Bulk upload cancelled.', 'info')
    if event_id:
        return redirect(url_for('admin.event_detail', event_id=event_id))
    return redirect(url_for('admin.dashboard'))


# ==================== TEMPLATE CONFIGURATION ====================

@admin_bp.route('/events/<int:event_id>/configure-template', methods=['GET', 'POST'])
@login_required
def configure_template(event_id):
    """
    Configure certificate template for an event.
    GET: Show template configuration page with upload and positioning.
    POST: Save name position and font settings.
    """
    from app.utils.certificate_generator import get_available_fonts
    
    event = Event.query.get_or_404(event_id)
    available_fonts = get_available_fonts()
    
    if request.method == 'POST':
        # Get position data from form
        try:
            x_percent = float(request.form.get('name_x', 50))
            y_percent = float(request.form.get('name_y', 50))
            font_size = int(request.form.get('font_size', 36))
            font_color = request.form.get('font_color', '#000000')
            font_name = request.form.get('font_name', 'helv')
        except (ValueError, TypeError):
            flash('Invalid position or font values.', 'error')
            return render_template('admin/configure_template.html', event=event, fonts=available_fonts)
        
        # Validate ranges
        x_percent = max(0, min(100, x_percent))
        y_percent = max(0, min(100, y_percent))
        font_size = max(8, min(200, font_size))
        
        # Validate hex color
        if not font_color.startswith('#') or len(font_color) != 7:
            font_color = '#000000'
        
        # Validate font name
        if font_name not in available_fonts:
            font_name = 'helv'
        
        # Update event
        event.name_position_x = x_percent
        event.name_position_y = y_percent
        event.font_size = font_size
        event.font_color = font_color
        event.font_name = font_name
        
        log_admin_action(
            admin_id=session.get('admin_id'),
            action='configure_template',
            details=f'Configured template for event: {event.name} (x={x_percent}%, y={y_percent}%, size={font_size}, font={font_name})',
            ip_address=request.remote_addr
        )
        db.session.commit()
        
        flash('Template configuration saved successfully!', 'success')
        return redirect(url_for('admin.event_detail', event_id=event_id))
    
    return render_template('admin/configure_template.html', event=event, fonts=available_fonts)


@admin_bp.route('/events/<int:event_id>/upload-template', methods=['POST'])
@login_required
def upload_template(event_id):
    """
    Upload a PNG template for an event.
    """
    event = Event.query.get_or_404(event_id)
    
    if 'template' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('admin.configure_template', event_id=event_id))
    
    file = request.files['template']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin.configure_template', event_id=event_id))
    
    if not allowed_template_file(file.filename):
        flash('Only PNG files are allowed for templates.', 'error')
        return redirect(url_for('admin.configure_template', event_id=event_id))
    
    # Delete old template if exists
    if event.template_filename:
        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', event.template_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
    
    # Create templates directory if needed
    templates_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Save with unique filename
    filename = generate_unique_filename(file.filename, prefix=f'template_{event.id}')
    template_path = os.path.join(templates_dir, filename)
    file.save(template_path)
    
    # Update event
    event.template_filename = filename
    
    # Set default position if not set
    if event.name_position_x is None:
        event.name_position_x = 50.0
    if event.name_position_y is None:
        event.name_position_y = 50.0
    
    log_admin_action(
        admin_id=session.get('admin_id'),
        action='upload_template',
        details=f'Uploaded template for event: {event.name}',
        ip_address=request.remote_addr
    )
    db.session.commit()
    
    flash('Template uploaded successfully! Now configure the name position.', 'success')
    return redirect(url_for('admin.configure_template', event_id=event_id))


@admin_bp.route('/events/<int:event_id>/template-preview')
@login_required
def template_preview(event_id):
    """
    Serve the template image directly for preview.
    """
    event = Event.query.get_or_404(event_id)
    
    if not event.template_filename:
        return Response('No template', status=404)
    
    template_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', event.template_filename)
    
    if not os.path.exists(template_path):
        return Response('Template not found', status=404)
    
    # Serve the image directly for preview
    from flask import send_file
    return send_file(
        template_path,
        mimetype='image/png'
    )


@admin_bp.route('/events/<int:event_id>/delete-template', methods=['POST'])
@login_required
def delete_template(event_id):
    """
    Delete the template from an event.
    """
    event = Event.query.get_or_404(event_id)
    
    if event.template_filename:
        template_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', event.template_filename)
        if os.path.exists(template_path):
            try:
                os.remove(template_path)
            except OSError:
                pass
        
        event.template_filename = None
        event.name_position_x = None
        event.name_position_y = None
        
        log_admin_action(
            admin_id=session.get('admin_id'),
            action='delete_template',
            details=f'Deleted template for event: {event.name}',
            ip_address=request.remote_addr
        )
        db.session.commit()
        
        flash('Template deleted.', 'success')
    
    return redirect(url_for('admin.event_detail', event_id=event_id))

