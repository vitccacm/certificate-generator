#!/usr/bin/env python
"""
WSGI Entry Point for local development and standard WSGI servers.
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
