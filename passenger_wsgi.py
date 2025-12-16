#!/usr/bin/env python
"""
Passenger WSGI Entry Point for cPanel Deployment.
This file is specifically for cPanel Python App with Passenger.
Compatible with Python 3.7+
"""
import sys
import os

# Update this path to match your cPanel virtual environment
# For cPanel: ~/virtualenv/appname/pythonversion/bin/python
INTERP = os.path.expanduser("~/virtualenv/certificate/3.7/bin/python")

if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Add path to the application
sys.path.insert(0, os.path.dirname(__file__))

# Import the application
from app import create_app

# Create the application instance
app = create_app('production')

# Handle subdirectory deployment
def application(environ, start_response):
    # Set SCRIPT_NAME for subdirectory deployment
    # Update this path to match your Application URL in cPanel
    environ['SCRIPT_NAME'] = '/certificate/v1'
    return app(environ, start_response)
