"""
WSGI Entry Point for cPanel LiteSpeed Server
Simple and compatible with Python 3.7+
"""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

# Set production mode
os.environ['FLASK_ENV'] = 'production'

# Create Flask app - variable MUST be named 'application'
from app import create_app
application = create_app('production')
