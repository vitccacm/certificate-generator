# Certificate Verification (QR + token) — Design

**Date:** 2026-06-02
**Status:** Approved design, pending implementation plan

## Summary

Add an optional, per-event certificate authenticity feature. When an admin enables it for an
event, every generated certificate gets a **QR code** baked into the image server-side. Scanning the
QR opens a public verify page (pre-loaded with the certificate's code and a security token); the
visitor solves the existing math captcha and sees the certificate's full details if it is authentic.

There is **no human-readable code printed** on the certificate — verification is QR-only.

## Goals

- Admin can enable verification per event and visually position the QR on the certificate template,
  reusing the existing click-to-position UI.
- The QR is rendered into the certificate **entirely in the backend** when enabled. The recipient
  has no input or control over whether/where it appears.
- The QR encodes `/verify/<code>?token=<token>` where:
  - `<code>` is the participant's id zero-padded to 6 digits (e.g. participant `424` → `000424`),
    derived, never stored.
  - `<token>` is derived from the participant's email + a hardcoded project secret, so verify links
    cannot be forged or enumerated.
- A public verify page validates the code+token (behind the math captcha) and, on success, shows
  full certificate details.

## Non-goals

- No cryptographic certificate signing beyond the HMAC token (the token authenticates the verify
  *link*, not the rendered image pixels).
- No change to the client-side `certificate_canvas.js` renderer — it is off the active download
  path, so it will not draw the QR. The active path is the server-rendered
  `/preview/<participant_id>` PNG.
- No manual code-entry verification — there is no printed code, so the verify page is reached only by
  scanning the QR.
- No token expiry/revocation (token is deterministic per email).

## Architecture overview

The certificate the user previews and downloads is the **server-rendered PNG** from the
`public.preview_certificate` route, produced by `generate_certificate_png()` (Pillow). Both the
"Download PNG" and "Download PDF" buttons fetch that same server image. Therefore the QR is drawn in
`generate_certificate_png()` and requires no client-side work.

New dependency: **`qrcode`** (pure-Python QR generation; renders to a Pillow image — Pillow is
already a dependency).

## The verification token

**The secret lives in `app/config.py`**, following the existing `SECRET_KEY` convention:

```python
# Set VERIFY_TOKEN_SECRET in prod; falls back to SECRET_KEY so there is never an
# empty-key path that would let anyone forge verification tokens.
VERIFY_TOKEN_SECRET = os.environ.get('VERIFY_TOKEN_SECRET') or SECRET_KEY
```

The project owner sets `VERIFY_TOKEN_SECRET` at production deployment (via env var). If left
unset it falls back to `SECRET_KEY` (also mandatory in prod) rather than an empty string — this
closes the silent empty-HMAC-key footgun where anyone could forge tokens. `verify_token` also
**fails closed**, returning `False` if the resolved secret is ever empty. Documented in
`.env.example`.

A new module **`app/utils/verification.py`** owns the helpers and reads the secret from
`current_app.config['VERIFY_TOKEN_SECRET']` (both code paths — QR generation during preview/download
and token check during verify — run inside an app/request context):

- `generate_token(email) -> str` — `HMAC-SHA256(key=secret, msg=email.strip().lower())`, hex digest
  truncated to 16 chars (keeps the QR small and scannable).
- `verify_token(email, token) -> bool` — recompute and compare with `hmac.compare_digest`
  (constant-time).
- `format_code(participant_id) -> str` — `f"{participant_id:06d}"`.
- `parse_code(code) -> int | None` — strip, require all-digits, `int()`; return `None` on bad input.

Rotating the secret invalidates all previously issued QR links (expected behavior). Note: while the
secret is blank (dev), generation and verification stay internally consistent (both use the blank
key), so the flow still works — it just isn't secure until a real secret is set in prod.

## Data model — new `Event` columns

Added via a new `migrate_v3.py` following the existing `migrate_v2.py` pattern (SQLite
`ALTER TABLE ... ADD COLUMN`, idempotent column-existence checks, automatic backup). Also reflected
in `app/models.py`.

| Column | Type | Default | Purpose |
|---|---|---|---|
| `verify_enabled` | Boolean | `0` | Whether verification is on for this event |
| `qr_position_x` | Float | `85` | QR center X, % of width |
| `qr_position_y` | Float | `85` | QR center Y, % of height |
| `qr_size` | Float | `12` | QR width as % of certificate width |

No code-text columns — nothing is printed on the certificate besides the QR.

## Certificate rendering (`app/utils/certificate_generator.py`)

`generate_certificate_png()` gains optional keyword params (all default to "off" so existing calls
are unaffected):

- `verify_enabled` (bool)
- `qr_url` (str) — the full external verify URL the QR encodes
- `qr_x_percent`, `qr_y_percent`, `qr_size_percent` (float)

When `verify_enabled` is true: generate the QR for `qr_url` with the `qrcode` library, render to a
Pillow image, resize to `qr_size_percent`% of the certificate width (square), and paste it centered
on `(qr_x_percent, qr_y_percent)`. The name overlay behavior is unchanged; the QR is layered on top
afterward. QR failure is logged and degrades gracefully (certificate still renders without the QR)
consistent with the existing defensive `try/except`.

The `qr_url` is built by the route (which has request context):
`url_for('public.verify', code=format_code(participant.id), _external=True)` plus
`?token=<generate_token(participant.email)>`, and passed into the generator — the generator stays
free of request/`url_for` coupling.

Both `public.preview_certificate` and `public.download_certificate` call
`generate_certificate_png()`; both pass the QR params when `event.verify_enabled`, so preview and
download stay identical.

## Admin configuration UI (`app/templates/admin/configure_template.html`)

Extend the existing positioning page:

- An **"Enable certificate verification"** checkbox (bound to `verify_enabled`).
- A **"Placing:"** selector (Name / QR): clicking the template preview sets the position of whichever
  element is selected. Markers overlaid on the preview: the existing sample-name text, and a square
  QR-box outline sized to `qr_size`.
- An input for **QR size** (% of width).
- The QR controls are de-emphasized/hidden when verification is off.

The `admin.configure_template` POST handler reads and validates the new fields (clamp percentages to
0–100, QR size to a sane range e.g. 3–40) and saves them on the event, alongside the existing
name-position save.

## Public verify flow (`app/routes/public.py`)

New routes on the `public` blueprint:

- **`GET /verify/<code>`** — read `token` from the query string. Render the verify page showing the
  math captcha, with `code` and `token` carried in hidden form fields. Do **not** reveal validity yet
  (captcha must be solved first). Always generate a fresh captcha.
- **`POST /verify/<code>`** — validate the captcha first (reusing `validate_captcha`). On captcha
  failure, re-show the form with a fresh captcha (code + token preserved). On captcha success:
  - `parse_code(code)` → participant id; look up the participant; require it exists, its event has
    `verify_enabled` true, and the event is visible.
  - `verify_token(participant.email, token)` must pass.
  - **Valid:** render the result state showing recipient name, event name, and issue date
    (`event.event_date` or `participant.created_at`) with a clear "Authentic" indicator.
  - **Invalid** (bad code format, no such participant, event not verify-enabled/invisible, or token
    mismatch): render a single generic "No valid certificate found" message — do not distinguish
    reasons, to avoid leaking which ids exist.
- **`GET /verify`** (optional landing) — a simple info page: "Scan the QR code on your certificate to
  verify it." No form (nothing to type).

New template **`app/templates/public/verify.html`** handles the captcha form, the result state, and
the info/landing state (extends `base.html`, matches the existing glass-card visual style).

A **"Verify"** link is added to the top nav (next to Home) and to the footer in `base.html`,
pointing at `GET /verify`.

## Error handling & edge cases

- Missing/empty/non-numeric/wrong-length code, or missing token → generic "not found".
- Code maps to a real participant whose event has `verify_enabled` false or is not visible → generic
  "not found".
- Token mismatch (forged/tampered link, or secret rotated) → generic "not found".
- Captcha is one-time and session-based (unchanged); a failed captcha preserves code+token and issues
  a fresh captcha.
- QR generation failure or missing `qrcode` lib is logged; the certificate still renders without the
  QR rather than 500-ing.

## Testing

**Automated**
- Token: `generate_token` is deterministic and case/whitespace-insensitive on email;
  `verify_token` accepts the matching token and rejects a tampered one.
- Code: `format_code`/`parse_code` round-trip; `parse_code` rejects non-6-digit / non-numeric input.
- `generate_certificate_png(verify_enabled=True, ...)` returns valid PNG bytes that differ from the
  no-QR render (QR actually drawn).
- Verify lookup: valid for an enabled event's participant with the correct token; not-found for
  unknown id, wrong token, `verify_enabled` false, or invisible event.

**Manual**
- Enable verification on an event, position Name/QR, set QR size, save.
- Download the certificate; confirm the QR appears at the configured spot.
- Scan the QR → lands on `/verify/000XXX?token=…` → solve captcha → see valid result with full
  details.
- Tamper with the token in the URL → generic not-found after captcha.

## Implementation surface (files)

- `requirements.txt` — add `qrcode`.
- `app/config.py` — add blank `VERIFY_TOKEN_SECRET` (env-backed, set at prod).
- `.env.example` — document `VERIFY_TOKEN_SECRET`.
- `migrate_v3.py` — new migration for the columns above.
- `app/models.py` — new `Event` columns.
- `app/utils/verification.py` — **new**: token/code helpers (read secret from app config).
- `app/utils/certificate_generator.py` — QR rendering in `generate_certificate_png()`.
- `app/routes/public.py` — pass QR params in preview/download; add `GET /verify`,
  `GET/POST /verify/<code>`.
- `app/routes/admin.py` — read/validate/save new fields in `configure_template`.
- `app/templates/admin/configure_template.html` — enable toggle, Name/QR selector, QR size control.
- `app/templates/public/verify.html` — **new**: verify page (info / captcha form / result).
- `app/templates/base.html` — "Verify" link in nav + footer.
