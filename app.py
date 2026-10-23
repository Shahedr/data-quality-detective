"""Vercel FastAPI root entrypoint for the free web app.

Vercel automatically configures the FastAPI application at this root path.
Runtime requests must preserve their original URL path (no catch-all rewrite).
Hosted uploads use the smaller request limit; large-file routes remain local.
"""
from webapp.app import app
