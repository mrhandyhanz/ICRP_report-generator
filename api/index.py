"""
Vercel Serverless Entry Point

This file bridges Vercel's serverless environment with the Flask app.

IMPORTANT LIMITATION:
Vercel serverless functions are STATELESS. This means:
- SQLite database resets on every cold start (no persistence)
- Uploaded files are lost between requests
- Generated PDFs are lost between requests

For production use, you should:
1. Use a cloud database (PostgreSQL, MySQL, etc.)
2. Use cloud file storage (S3, Cloudinary, etc.)
3. Or deploy on a traditional server (Railway, Render, Fly.io)
"""

import sys
import os

# Add the project root to the Python path
# so Flask can find app.py, templates/, static/, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects the Flask app to be exposed as 'app'
# This is the WSGI handler that Vercel calls
