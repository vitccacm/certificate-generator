# Certificate Download Portal

A Flask-based web application for managing and distributing event certificates with server-side CAPTCHA verification, dark/light mode UI, and comprehensive admin features.

## Features

### Public Portal
- **Event Cards**: Browse available events with name, description, and date
- **Email Verification**: Enter email + CAPTCHA to find certificate
- **PDF Preview**: View certificate before downloading
- **Secure Download**: Filename format: `StudentName_EventName.pdf`

### Admin Panel
- **Dashboard**: Overview of events, participants, downloads
- **Event Management**: Create, edit, toggle visibility, delete (password-protected)
- **Multi-PDF Upload**: Upload multiple certificate PDFs at once
- **Bulk Import**: CSV/Excel upload with preview validation
- **Single Participant**: Add individual participants with PDF
- **Admin Management**: Create/delete admin accounts, change passwords
- **Activity Logs**: Track all admin actions and downloads

### Security
- Password-protected admin actions
- Server-side CAPTCHA (no external services)
- Session-based authentication
- Secure file handling (certificates outside public folder)

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite (default)
- **Frontend**: Bootstrap 5, CSS with dark/light mode
- **CAPTCHA**: Python `captcha` package

---

## Local Development

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# 1. Navigate to project directory
cd /path/to/certificate

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database and create admin
python seed.py

# 5. Run development server
flask run --debug --port 5000
```

### Access
- **Public**: http://localhost:5000/
- **Admin**: http://localhost:5000/admin
- **Credentials**: `admin` / `admin123`

---
