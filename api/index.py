"""Vercel entrypoint: FastAPI sample-only public demo.

Production Vercel configuration MUST set DQD_PUBLIC_DEMO_ONLY=1.
Full workbook uploads and native Excel/VBA remain local-only.
"""

from webapp.app import app
