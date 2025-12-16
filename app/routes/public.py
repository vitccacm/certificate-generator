"""
Public routes for landing page and certificate download.
Includes CAPTCHA validation for download requests.
"""
import os
import io
from flask import (Blueprint, render_template, request, redirect, url_for, 
                   flash, current_app, send_file, session)
from app.models import db, Event, Participant
from app.utils.captcha import get_captcha_question, validate_captcha
from app.utils.helpers import validate_email, sanitize_email
from app.utils.certificate_generator import generate_certificate

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    """
    Public landing page showing all visible events as cards.
    """
    # Get only visible events for display
    events = Event.query.filter_by(is_visible=True).order_by(Event.created_at.desc()).all()
    return render_template('public/index.html', events=events)


@public_bp.route('/event/<int:event_id>', methods=['GET', 'POST'])
def download_page(event_id):
    """
    Event-specific download page with CAPTCHA.
    """
    # Verify event exists and is visible
    event = Event.query.filter_by(id=event_id, is_visible=True).first_or_404()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        captcha_input = request.form.get('captcha', '')
        
        # Validate CAPTCHA first (before any DB access)
        if not validate_captcha(captcha_input):
            flash('Incorrect answer. Please solve the math problem.', 'error')
            # Generate new CAPTCHA for retry
            captcha_question = get_captcha_question()
            return render_template('public/download.html', event=event, captcha_question=captcha_question)
        
        # Validate email
        if not email:
            flash('Please enter your email address.', 'error')
            captcha_question = get_captcha_question()
            return render_template('public/download.html', event=event, captcha_question=captcha_question)
        
        if not validate_email(email):
            flash('Please enter a valid email address.', 'error')
            captcha_question = get_captcha_question()
            return render_template('public/download.html', event=event, captcha_question=captcha_question)
        
        # Sanitize email
        email = sanitize_email(email)
        
        # Find participant
        participant = Participant.query.filter_by(
            event_id=event_id, 
            email=email
        ).first()
        
        if not participant:
            flash('No certificate found for this email address. Please check your email and try again.', 'error')
            captcha_question = get_captcha_question()
            return render_template('public/download.html', event=event, captcha_question=captcha_question)
        
        # For template-based participants (no certificate_filename), skip file check
        # Certificate will be generated dynamically on download
        if participant.certificate_filename:
            # Verify certificate file exists (only for custom certificates)
            cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], 
                                    participant.certificate_filename)
            if not os.path.exists(cert_path):
                flash('Certificate file not found. Please contact the administrator.', 'error')
                captcha_question = get_captcha_question()
                return render_template('public/download.html', event=event, captcha_question=captcha_question)
        elif not event.has_template:
            # No certificate file and no template - something is wrong
            flash('Certificate not available. Please contact the administrator.', 'error')
            captcha_question = get_captcha_question()
            return render_template('public/download.html', event=event, captcha_question=captcha_question)
        
        # Redirect to certificate view page
        return redirect(url_for('public.view_certificate', participant_id=participant.id))
    
    # GET request - generate new CAPTCHA
    captcha_question = get_captcha_question()
    return render_template('public/download.html', event=event, captcha_question=captcha_question)


@public_bp.route('/certificate/<int:participant_id>')
def view_certificate(participant_id):
    """
    Separate page to view certificate with preview and download option.
    """
    participant = Participant.query.get_or_404(participant_id)
    event = participant.event
    
    # Verify event is still visible
    if not event.is_visible:
        flash('This event is no longer available.', 'error')
        return redirect(url_for('public.index'))
    
    # Verify certificate availability
    if participant.certificate_filename:
        # Custom certificate - check file exists
        cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], 
                                participant.certificate_filename)
        if not os.path.exists(cert_path):
            flash('Certificate file not found.', 'error')
            return redirect(url_for('public.index'))
    elif not event.has_template:
        # No certificate file and no template
        flash('Certificate not available.', 'error')
        return redirect(url_for('public.index'))
    
    return render_template('public/certificate_view.html', 
                         participant=participant,
                         event=event)


@public_bp.route('/preview/<int:participant_id>')
def preview_certificate(participant_id):
    """
    Serve certificate PDF for preview (inline display).
    Supports both template-based (dynamic generation) and pre-uploaded certificates.
    """
    participant = Participant.query.get_or_404(participant_id)
    event = participant.event
    
    # Verify event is still visible
    if not event.is_visible:
        flash('This event is no longer available.', 'error')
        return redirect(url_for('public.index'))
    
    # Check if this is a template-based participant
    if event.has_template and not participant.certificate_filename:
        # Generate certificate dynamically from template
        template_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', event.template_filename)
        
        if not os.path.exists(template_path):
            flash('Certificate template not found.', 'error')
            return redirect(url_for('public.index'))
        
        if event.name_position_x is None or event.name_position_y is None:
            flash('Certificate template not properly configured.', 'error')
            return redirect(url_for('public.index'))
        
        cert_bytes = generate_certificate(
            template_path=template_path,
            participant_name=participant.name,
            x_percent=event.name_position_x,
            y_percent=event.name_position_y,
            font_size=event.font_size or 36,
            font_color=event.font_color or '#000000',
            font_name=event.font_name or 'helv'
        )
        
        if cert_bytes is None:
            flash('Could not generate certificate.', 'error')
            return redirect(url_for('public.index'))
        
        return send_file(
            io.BytesIO(cert_bytes),
            mimetype='application/pdf'
        )
    else:
        # Custom certificate - serve from file
        if not participant.certificate_filename:
            flash('Certificate not available.', 'error')
            return redirect(url_for('public.index'))
        
        cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], 
                                participant.certificate_filename)
        
        if not os.path.exists(cert_path):
            flash('Certificate file not found.', 'error')
            return redirect(url_for('public.index'))
        
        # Serve file inline for preview
        return send_file(
            cert_path,
            mimetype='application/pdf'
        )


@public_bp.route('/download/<int:participant_id>')
def download_certificate(participant_id):
    """
    Download certificate PDF with proper filename.
    Tracks download count.
    Supports both template-based (dynamic generation) and pre-uploaded certificates.
    """
    participant = Participant.query.get_or_404(participant_id)
    event = participant.event
    
    # Verify event is still visible
    if not event.is_visible:
        flash('This event is no longer available.', 'error')
        return redirect(url_for('public.index'))
    
    # Create download filename: name_of_student_name_of_event.pdf
    student_name = participant.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    event_name = event.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    download_filename = f"{student_name}_{event_name}.pdf"
    
    # Check if this is a template-based event (no individual certificate file)
    if event.has_template and not participant.certificate_filename:
        # Generate certificate dynamically from template
        template_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', event.template_filename)
        
        if not os.path.exists(template_path):
            flash('Certificate template not found.', 'error')
            return redirect(url_for('public.index'))
        
        # Verify template configuration is complete
        if event.name_position_x is None or event.name_position_y is None:
            flash('Certificate template not properly configured.', 'error')
            return redirect(url_for('public.index'))
        
        # Generate the certificate with participant's name
        cert_bytes = generate_certificate(
            template_path=template_path,
            participant_name=participant.name,
            x_percent=event.name_position_x,
            y_percent=event.name_position_y,
            font_size=event.font_size or 36,
            font_color=event.font_color or '#000000',
            font_name=event.font_name or 'helv'
        )
        
        if cert_bytes is None:
            flash('Could not generate certificate.', 'error')
            return redirect(url_for('public.index'))
        
        # Track download
        ip_address = request.remote_addr
        participant.increment_download(ip_address=ip_address)
        db.session.commit()
        
        # Serve generated certificate
        return send_file(
            io.BytesIO(cert_bytes),
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/pdf'
        )
    else:
        # Traditional: serve pre-uploaded certificate file
        if not participant.certificate_filename:
            flash('Certificate file not found.', 'error')
            return redirect(url_for('public.index'))
        
        cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], 
                                participant.certificate_filename)
        
        if not os.path.exists(cert_path):
            flash('Certificate file not found.', 'error')
            return redirect(url_for('public.index'))
        
        # Track download
        ip_address = request.remote_addr
        participant.increment_download(ip_address=ip_address)
        db.session.commit()
        
        # Serve the file as download
        return send_file(
            cert_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/pdf'
        )


# ==================== ERROR HANDLERS ====================

@public_bp.app_errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404


@public_bp.app_errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    db.session.rollback()
    return render_template('errors/500.html'), 500
