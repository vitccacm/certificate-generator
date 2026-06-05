# Certificate Notification Emails

**Date:** 2026-06-05
**Status:** Approved

## Goal

Admins can email participants a link to download their certificate, from a new
per-event "Send Emails" page. Targets: manually selected students, all
students, or all who have not downloaded yet. Emails are HTML, branded, and
include the download link plus step-by-step instructions. Every send is logged
(per-participant + activity log) and surfaced on the event detail page.

## Constraints

- Shared hosting (Passenger/cPanel): no long-running requests, no reliable
  background threads, avoid new dependencies.
- Emails must be sent from the backend; the frontend must show live progress.

## Architecture

Single streaming request (revised 2026-06-05 per user request): the Send
Emails page posts ALL selected participant IDs in one request. The backend
opens ONE SMTP connection (reading the MAIL_* settings from app config at
that moment), sends every email over it, and closes the connection at the
end. As each email is sent it streams one NDJSON result line to the browser,
which updates a live progress bar and per-row status. Streaming keeps data
flowing every ~MAIL_SEND_DELAY seconds, so inter-packet proxy timeouts do not
trigger even for large batches.

## Components

### 1. SMTP configuration (`app/config.py`)

Hardcoded directly in the base `Config` class (revised 2026-06-05 per user
request — values are literals, not env lookups). The repository ships with
`your-...` placeholders; the real credentials are edited into `config.py`
on the server only, never committed to git.

| Key | Shipped value | Meaning |
|---|---|---|
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP host |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USE_TLS` | `True` | STARTTLS |
| `MAIL_USE_SSL` | `False` | implicit SSL (SMTPS) |
| `MAIL_USERNAME` | `your-email@gmail.com` | SMTP login (placeholder) |
| `MAIL_PASSWORD` | `your-app-password` | SMTP password (placeholder) |
| `MAIL_SENDER_NAME` | `ACM SC VITC` | From display name |
| `MAIL_DEFAULT_SENDER` | `''` | From address; falls back to `MAIL_USERNAME` |
| `MAIL_SEND_DELAY` | `1.0` | Seconds to sleep between consecutive sends |

`is_mail_configured()` treats empty values OR `your-...` placeholders as
unconfigured: the Send Emails page shows an "SMTP not configured" notice and
sending is disabled until the placeholders are replaced. No silent failures,
and no accidental sends with placeholder credentials.

### 2. `EmailLog` model (`app/models.py`) + `migrate_v4.py`

```python
class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    id             Integer PK
    participant_id Integer FK participants.id, nullable=False
    admin_id       Integer FK admins.id, nullable=True
    sent_at        DateTime, default utcnow
    status         String(10)  # 'sent' | 'failed'
    error          Text, nullable
```

- `Participant.email_logs` relationship (dynamic, cascade delete-orphan).
- `Participant.emails_sent_count` property: count of `status == 'sent'` rows.
- `Participant.last_emailed_at` property: latest `sent_at` of a sent row, or None.
- `migrate_v4.py` creates the table, following the migrate_v2/v3 pattern.

### 3. Mailer (`app/utils/mailer.py`)

Stdlib only (`smtplib`, `email.mime`) — no new dependency.

- `is_mail_configured()` → bool (server + username present).
- `iter_certificate_emails(participants, event, admin_id)` → generator
  yielding one `{participant_id, status, error}` dict per participant:
  - Opens ONE SMTP connection for the WHOLE batch when iteration starts
    (SSL or TLS per config) and closes it when the batch ends — including
    early termination (try/finally).
  - For each participant: render HTML + plain-text alternative, send,
    add an `EmailLog` row ('sent' or 'failed' + error), yield the result
    (the route commits per result so progress survives interruption).
  - Sleeps `MAIL_SEND_DELAY` seconds between sends (not after the last).
  - Connection-level failures (auth, refused, lost mid-batch) raise
    `MailConnectionError` so the route emits a stream-level error and stops.

### 4. Email template (`app/templates/email/certificate_email.html`)

Inline-styled, email-client-safe HTML:

- ACM SC VITC header, "Hi {{ participant.name }}"
- Event name + date
- "Download your certificate" button → event download page
  (`public.download_page`, `_external=True`; includes `?token=` for protected
  events)
- Numbered steps: open the link → enter this email address → solve the quick
  check → view and download
- Plain-text URL fallback + plain-text MIME part
- The link intentionally points at the event download page (not a direct file
  URL) so the existing email+captcha verification and download logging stay
  intact.

### 5. Routes (`app/routes/admin.py`)

- `GET /admin/events/<id>/emails` — Send Emails page. Blocked (redirect with
  flash) for archived events. Passes participants + mail-configured flag.
- `POST /admin/events/<id>/emails/send` — streaming NDJSON API for the
  whole batch:
  - Request: `{participant_ids: [...]}` (all selected IDs at once)
  - Only IDs belonging to this event are accepted; others reported as
    failed "Participant not found".
  - Response: `application/x-ndjson` stream — one
    `{participant_id, status, error}` line per email as it is sent, then
    `{"event": "done", "sent": N, "failed": M}`. On connection-level SMTP
    failure an `{"event": "error", "error": msg}` line is emitted and the
    batch stops.
  - Activity log: one `AdminLog` entry created when the batch starts; its
    details are updated with running totals ("42 sent, 2 failed of 180")
    and committed per result, so the totals are accurate even if the
    browser disconnects mid-batch.

### 6. Send Emails page (`app/templates/admin/send_emails.html`)

- Linked from a new "Email Certificates" card on the event detail page.
- Table: checkbox | name | email | downloads | emails sent | last emailed.
- Toolbar: Select all / Select not downloaded / Clear + live "N selected".
- Send button (confirm prompt) → JS posts all selected IDs in one request
  and reads the NDJSON response stream incrementally: live progress bar
  ("42/180 sent, 2 failed"), per-row ✓/✗ as each result line arrives,
  failed rows stay selectable for retry.
- "SMTP not configured" alert + disabled controls when mail is not set up.
- Archived events cannot reach this page.

### 7. Event detail page additions (`event_detail.html`)

- "Email Certificates" card (next to Bulk Import): shows total emails sent for
  the event + "Send Emails" button to the new page. Locked when archived.
- Participants table: new "Emails" column — sent count badge, with last-sent
  date in the tooltip. `0` shown as muted dash.

## Error handling

- SMTP connection/auth failure → an `{"event": "error"}` line is streamed;
  UI halts the batch and shows the error.
- Per-recipient rejection → logged as `failed` EmailLog with error, batch
  continues on the same connection.
- Participant deleted mid-batch / wrong event → ID skipped, reported as failed
  with "not found".
- CSRF/auth: routes behind `@login_required` like all admin routes.

## Testing / verification

- Manual verification with a local debug SMTP server
  (`python -m smtpd`-equivalent / `aiosmtpd`) capturing messages: send to a
  seeded event, confirm EmailLog rows, AdminLog batch row updates, UI progress,
  and the rendered email HTML (link + token correctness for protected events).
- Edge checks: unconfigured SMTP state, archived event, failed recipient.

## Rejected alternatives

- **Flask-Mail** — stdlib smtplib suffices; one less cPanel dependency.
- **Background thread + polling** — Passenger may recycle workers mid-send;
  chunked synchronous requests are reliable and still give live updates.
- **AdminLog-only logging (no EmailLog table)** — cannot show per-participant
  email status on the event page.
- **Direct certificate link in the email** — would bypass the captcha + email
  verification flow and its download logging.
