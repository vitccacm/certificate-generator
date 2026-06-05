"""
Certificate notification email sender.

Uses the standard library (smtplib + email.mime) so no extra dependency is
needed on shared hosting. SMTP settings come from app config (MAIL_* keys,
see app/config.py). One SMTP connection is reused for a whole chunk of
recipients, with MAIL_SEND_DELAY seconds between consecutive sends to stay
under provider rate limits.
"""
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from flask import current_app, render_template, url_for

from app.models import db, EmailLog


class MailConnectionError(Exception):
    """Connection-level SMTP failure (auth, refused, TLS) - the whole batch
    should stop rather than logging a failure per recipient."""


def is_mail_configured():
    """Return True if SMTP is configured enough to attempt sending.

    The shipped config.py contains "your-..." placeholders; sending stays
    disabled until they are replaced with real credentials.
    """
    cfg = current_app.config
    server = cfg.get('MAIL_SERVER') or ''
    username = cfg.get('MAIL_USERNAME') or ''
    password = cfg.get('MAIL_PASSWORD') or ''
    if not server or not username:
        return False
    return not any(v.startswith('your-') for v in (username, password))


def _sender_address():
    cfg = current_app.config
    return cfg.get('MAIL_DEFAULT_SENDER') or cfg.get('MAIL_USERNAME')


def build_download_url(event):
    """Absolute URL of the event download page (with token when protected)."""
    kwargs = {'event_id': event.id, '_external': True}
    if event.is_protected and event.access_token:
        kwargs['token'] = event.access_token
    return url_for('public.download_page', **kwargs)


def _build_message(participant, event, download_url):
    """Build the multipart (plain + HTML) certificate email."""
    cfg = current_app.config
    subject = f"Your certificate for {event.name} is ready"

    html_body = render_template(
        'email/certificate_email.html',
        participant=participant, event=event, download_url=download_url,
    )
    text_body = (
        f"Hi {participant.name},\n\n"
        f"Your certificate for {event.name} is ready to download.\n\n"
        f"How to download:\n"
        f"1. Open this link: {download_url}\n"
        f"2. Enter this email address ({participant.email})\n"
        f"3. Solve the quick verification check\n"
        f"4. View and download your certificate\n\n"
        f"Regards,\n{cfg.get('MAIL_SENDER_NAME')}\n"
    )

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr((cfg.get('MAIL_SENDER_NAME'), _sender_address()))
    msg['To'] = participant.email
    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    return msg


def _open_connection():
    """Open and authenticate an SMTP connection per config.

    Raises MailConnectionError on any connection-level problem.
    """
    cfg = current_app.config
    try:
        if cfg.get('MAIL_USE_SSL'):
            smtp = smtplib.SMTP_SSL(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=30)
        else:
            smtp = smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=30)
            if cfg.get('MAIL_USE_TLS'):
                smtp.starttls()
        if cfg.get('MAIL_PASSWORD'):
            smtp.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
        return smtp
    except (smtplib.SMTPException, OSError) as e:
        raise MailConnectionError(f"Could not connect to SMTP server: {e}") from e


def iter_certificate_emails(participants, event, admin_id=None):
    """
    Generator that emails each participant their certificate link over a
    SINGLE SMTP connection: the connection is opened once when sending
    starts (reading the SMTP settings from app config at that moment),
    every email is sent over it with MAIL_SEND_DELAY seconds between
    consecutive sends, and it is closed when the batch ends - including
    when the consumer stops iterating early.

    Yields one {participant_id, status, error} dict per participant as each
    email is attempted. An EmailLog row is added to the session before each
    yield; the caller is expected to commit per result so progress is
    persisted even if the batch is interrupted.

    Raises MailConnectionError if the connection cannot be established
    (nothing sent or logged) or if it is lost mid-batch (the failed
    attempt is logged and yielded first).
    """
    if not is_mail_configured():
        raise MailConnectionError("SMTP is not configured (MAIL_SERVER/MAIL_USERNAME missing)")

    delay = max(0.0, float(current_app.config.get('MAIL_SEND_DELAY', 1.0)))
    download_url = build_download_url(event)

    smtp = _open_connection()
    try:
        for i, participant in enumerate(participants):
            if i > 0 and delay:
                time.sleep(delay)
            try:
                msg = _build_message(participant, event, download_url)
                smtp.sendmail(_sender_address(), [participant.email], msg.as_string())
                status, error = 'sent', None
            except smtplib.SMTPServerDisconnected as e:
                # Connection died mid-batch: log this one as failed, then stop
                db.session.add(EmailLog(participant_id=participant.id, admin_id=admin_id,
                                        status='failed', error=str(e)))
                yield {'participant_id': participant.id,
                       'status': 'failed', 'error': str(e)}
                raise MailConnectionError(f"SMTP connection lost: {e}") from e
            except (smtplib.SMTPException, OSError) as e:
                status, error = 'failed', str(e)

            db.session.add(EmailLog(participant_id=participant.id, admin_id=admin_id,
                                    status=status, error=error))
            yield {'participant_id': participant.id,
                   'status': status, 'error': error}
    finally:
        try:
            smtp.quit()
        except Exception:
            pass
