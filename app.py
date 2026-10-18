"""Vercel FastAPI root entrypoint for the public sample-only demo.

Vercel automatically configures the FastAPI application at this root path.
Runtime requests must preserve their original URL path (no catch-all rewrite).
On Vercel, webapp.app always disables user file uploads.
"""
from webapp.app import app
