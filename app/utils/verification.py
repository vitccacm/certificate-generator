"""
Certificate verification helpers.

A certificate's QR code encodes /verify/<code>?token=<token> where:
  - <code>  is the participant id zero-padded to 6 digits (e.g. 424 -> "000424").
  - <token> is an HMAC of the recipient's email keyed by VERIFY_TOKEN_SECRET,
            so verification links cannot be forged or enumerated.

The secret lives in app/config.py (VERIFY_TOKEN_SECRET) and is read from the
active app config at runtime.
"""
import hmac
import hashlib

from flask import current_app

# Length (hex chars) of the truncated token embedded in the QR. 16 hex chars
# (64 bits) keeps the QR small/scannable while remaining hard to guess.
TOKEN_LENGTH = 16

CODE_DIGITS = 6


def _get_secret():
    """Return the configured verification secret (may be '' in dev)."""
    return current_app.config.get('VERIFY_TOKEN_SECRET', '') or ''


def generate_token(email):
    """
    Derive the verification token for a recipient email.

    Deterministic: the same email always yields the same token (until the
    secret is rotated). Email is normalised (stripped + lowercased) so it
    matches regardless of casing/whitespace differences.
    """
    normalized = (email or '').strip().lower()
    digest = hmac.new(
        _get_secret().encode('utf-8'),
        normalized.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return digest[:TOKEN_LENGTH]


def verify_token(email, token):
    """Return True if `token` matches the expected token for `email`."""
    if not token:
        return False
    # Fail closed: never validate tokens when no secret is configured, otherwise
    # an empty HMAC key would let anyone forge a valid token.
    if not _get_secret():
        return False
    expected = generate_token(email)
    # Constant-time comparison to avoid timing leaks.
    return hmac.compare_digest(expected, str(token).strip())


def format_code(participant_id):
    """Format a participant id as a zero-padded 6-digit code (424 -> '000424')."""
    return f"{int(participant_id):0{CODE_DIGITS}d}"


def parse_code(code):
    """
    Parse a verification code back into a participant id.

    Returns the integer id, or None if the code is missing/non-numeric.
    """
    if code is None:
        return None
    code = str(code).strip()
    if not code.isdigit():
        return None
    return int(code)
