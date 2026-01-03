"""
Public routes for landing page and certificate download.
Includes CAPTCHA validation for download requests.
"""
import os
import io
from flask import (Blueprint, render_template, request, redirect, url_for, 
                   flash, current_app, send_file, session, Response, abort)
from app.models import db, Event, Participant
from app.utils.captcha import get_captcha_question, validate_captcha
from app.utils.helpers import validate_email, sanitize_email
from app.utils.certificate_generator import generate_certificate_png

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    """
    Public landing page showing all visible events as cards.
    Protected events are excluded. Archived events shown separately.
    """
    # Get only visible, non-protected, non-archived events for main display
    events = Event.query.filter_by(
        is_visible=True, 
        is_protected=False,
        is_archived=False
    ).order_by(Event.created_at.desc()).all()
    
    # Get archived events that should be shown on homepage
    archived_events = Event.query.filter_by(
        is_archived=True,
        show_in_archive=True
    ).order_by(Event.archived_at.desc()).all()
    
    return render_template('public/index.html', events=events, archived_events=archived_events)


@public_bp.route('/event/<int:event_id>', methods=['GET', 'POST'])
def download_page(event_id):
    """
    Event-specific download page with CAPTCHA.
    Protected events require valid access token.
    Archived events with show_in_archive show a message that downloads are disabled.
    """
    event = Event.query.get_or_404(event_id)
    
    # Archived events with show_in_archive can be viewed but not downloaded
    if event.is_archived:
        if event.show_in_archive:
            # Show archived message page
            return render_template('public/download.html', event=event, 
                                 captcha_question=None, archived_no_download=True)
        else:
            abort(404)  # Not visible at all
    
    # Check visibility - event must be visible
    if not event.is_visible:
        abort(404)
    
    # Check if protected event - require valid token
    if event.is_protected:
        token = request.args.get('token', '')
        if not token or token != event.access_token:
            abort(404)  # Don't reveal that the event exists
    
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
    import logging
    
    participant = Participant.query.get_or_404(participant_id)
    event = participant.event
    
    logging.info(f"Preview certificate for participant {participant_id}: {participant.name}")
    logging.info(f"Event: {event.name}, has_template: {event.has_template}, template_filename: {event.template_filename}")
    logging.info(f"Participant certificate_filename: {participant.certificate_filename}")
    
    # Verify event is still visible
    if not event.is_visible:
        flash('This event is no longer available.', 'error')
        return redirect(url_for('public.index'))
    
    # Check if this is a template-based participant
    if event.has_template and not participant.certificate_filename:
        # Generate certificate dynamically from template
        template_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', event.template_filename)
        
        logging.info(f"Template path: {template_path}")
        logging.info(f"Template exists: {os.path.exists(template_path)}")
        
        if not os.path.exists(template_path):
            logging.error(f"Template file not found: {template_path}")
            flash('Certificate template not found.', 'error')
            return redirect(url_for('public.index'))
        
        if event.name_position_x is None or event.name_position_y is None:
            logging.error(f"Template not configured: x={event.name_position_x}, y={event.name_position_y}")
            flash('Certificate template not properly configured.', 'error')
            return redirect(url_for('public.index'))
        
        logging.info(f"Generating certificate with: x={event.name_position_x}, y={event.name_position_y}, font={event.font_name}")
        
        cert_bytes = generate_certificate_png(
            template_path=template_path,
            participant_name=participant.name,
            x_percent=event.name_position_x,
            y_percent=event.name_position_y,
            font_size=event.font_size or 36,
            font_color=event.font_color or '#000000',
            font_name=event.font_name or 'helv'
        )
        
        if cert_bytes is None:
            logging.error("Certificate generation returned None!")
            flash('Could not generate certificate.', 'error')
            return redirect(url_for('public.index'))
        
        logging.info(f"Certificate generated successfully, size: {len(cert_bytes)} bytes")
        
        # Use Response instead of send_file for Passenger WSGI compatibility
        response = Response(
            cert_bytes,
            mimetype='image/png'
        )
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
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
            mimetype='image/png'
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
    
    # Create download filename: name_of_student_name_of_event.png
    student_name = participant.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    event_name = event.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    download_filename = f"{student_name}_{event_name}.png"
    
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
        cert_bytes = generate_certificate_png(
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
        
        # Use Response instead of send_file for Passenger WSGI compatibility
        response = Response(
            cert_bytes,
            mimetype='image/png'
        )
        response.headers['Content-Disposition'] = f'attachment; filename="{download_filename}"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
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
            mimetype='image/png'
        )


# ==================== API ENDPOINTS ====================

@public_bp.route('/api/certificate-data/<int:participant_id>')
def get_certificate_data(participant_id):
    """
    API endpoint that returns certificate rendering data as JSON.
    Used for client-side canvas rendering.
    """
    from flask import jsonify
    
    participant = Participant.query.get_or_404(participant_id)
    event = participant.event
    
    # Verify event is visible
    if not event.is_visible:
        return jsonify({'error': 'Event not available'}), 404
    
    # Font mapping for CSS
    font_map = {
        'arial': 'Arial, sans-serif',
        'arial_bold': 'Arial, sans-serif',
        'times': '"Times New Roman", serif',
        'times_bold': '"Times New Roman", serif',
        'georgia': 'Georgia, serif',
        'verdana': 'Verdana, sans-serif',
        'tahoma': 'Tahoma, sans-serif',
        'courier': '"Courier New", monospace',
        'trebuchet': '"Trebuchet MS", sans-serif',
        'palatino': '"Palatino Linotype", serif',
        'garamond': 'Garamond, serif',
        'bookman': '"Bookman Old Style", serif',
        'century': '"Century Gothic", sans-serif',
        'lucida': '"Lucida Console", monospace',
    }
    
    # Check if custom certificate or template-based
    if participant.certificate_filename:
        # Custom certificate - serve via route
        cert_url = url_for('public.serve_certificate_file', filename=participant.certificate_filename)
        return jsonify({
            'type': 'custom',
            'certificate_url': cert_url,
            'name': participant.name
        })
    elif event.has_template:
        # Template-based - return data for client rendering
        template_url = url_for('public.serve_template', event_id=event.id)
        font_name = event.font_name or 'arial'
        font_weight = 'bold' if font_name.endswith('_bold') else 'normal'
        
        return jsonify({
            'type': 'template',
            'template_url': template_url,
            'name': participant.name,
            'x_percent': event.name_position_x or 50,
            'y_percent': event.name_position_y or 35,
            'font_size': event.font_size or 36,
            'font_color': event.font_color or '#000000',
            'font_family': font_map.get(font_name, 'Arial, sans-serif'),
            'font_weight': font_weight
        })
    else:
        return jsonify({'error': 'No certificate available'}), 404


@public_bp.route('/template/<int:event_id>')
def serve_template(event_id):
    """Serve template image for client-side rendering."""
    event = Event.query.get_or_404(event_id)
    
    if not event.is_visible or not event.template_filename:
        return '', 404
    
    template_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', event.template_filename)
    
    if not os.path.exists(template_path):
        return '', 404
    
    return send_file(template_path, mimetype='image/png')


@public_bp.route('/certificate-file/<filename>')
def serve_certificate_file(filename):
    """Serve custom certificate file."""
    cert_path = os.path.join(current_app.config['CERTIFICATES_FOLDER'], filename)
    
    if not os.path.exists(cert_path):
        return '', 404
    
    return send_file(cert_path, mimetype='image/png')


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

