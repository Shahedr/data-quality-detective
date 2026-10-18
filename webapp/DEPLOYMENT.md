# Deployment and distribution

## What is available

**Local full application** (Windows, macOS, Linux): CSV/XLSX/XLSM upload
analysis, all-sheet grid and audit exports. Windows users with desktop Excel
can separately launch supervised formula testing and explicitly approved VBA
checks. No workbook needs to leave the local computer for this workflow.

**Public web demo** (Vercel): a sample-only interactive web application.
It intentionally **rejects every user-upload endpoint with HTTP 403**.
Only bundled fictional CSV sample data is profiled, paged, and exported.
Excel/VBA execution is **never available through any web endpoint**.

Vercel sets the environment variable \`VERCEL\`, so the backend
**fails closed to sample-only mode** even if
\`DQD_PUBLIC_DEMO_ONLY\` was accidentally omitted. Other environments
can explicitly set \`DQD_PUBLIC_DEMO_ONLY=1\` to preview the hosted demo.

### Vercel deployment

The repository includes \`api/index.py\`, \`requirements.txt\`, and
\`vercel.json\`. Connect the \`main\` branch as a Vercel **FastAPI** project
with root directory at the repository root. Optionally set
\`DQD_PUBLIC_DEMO_ONLY=1\` for clarity and extra configuration visibility.
Keep the Vercel deployment sample-only.

Once deployed, verify:

- \`GET /\` loads the demo interface and **Explore interactive demo** works.
- \`GET /api/config\` reports \`public_demo\` and \`upload_allowed=false\`.
- \`GET /api/demo/analyze\` returns results for exactly 12 sample rows.
- \`GET /api/demo/rows?issue=duplicate\` returns 2 flagged rows.
- \`GET /api/demo/export/html\` and \`/api/demo/export/xlsx\` return sample reports.
- \`POST /api/analyze\` (even with arbitrary XLSM bytes) returns HTTP **403**.
- No macro execution or uploaded-file processing is exposed remotely.

Public Vercel hosting is NOT the finished commercial product. Do not advertise
private-dataset processing, customer isolation, enterprise compliance,
data-protection guarantees, billing, or production Excel execution.

## Windows: one-click full local version

1. Download the repository ZIP and extract the project to a folder.
2. Double-click \`INSTALL_ON_WINDOWS.cmd\` once to install dependencies.
3. Double-click \`START_DATA_QUALITY_DETECTIVE.cmd\` to launch the browser
   app automatically on the first free local port between 8000 and 8099.
4. Optionally double-click \`START_EXCEL_VALIDATOR.cmd\` to open real Excel
   calculation testing in a separate supervised Windows window.

The script always uses \`127.0.0.1\` (your own computer), never \`0.0.0.0\`.
Do not expose the local FastAPI server to the public internet.

## Requirements before a customer-upload SaaS launch

- Account sign-in, organization authorization, and tenant isolation.
- Authenticated uploads, measured bandwidth/CPU limits, async job queues,
  per-user quotas, and storage encryption/expiry/deletion.
- Threat modeling and an independent security review, including
  malicious uploads, decompression bombs, files with complex Excel objects,
  and denial-of-service risks.
- User consent, privacy/retention policy, logging/monitoring, incident response.
- Payment/webhook flow and operational tests.
- Separately isolated Windows execution hosts for untrusted VBA, if that
  feature is ever made available; **never run third-party VBA on the web app
  server or a normal user desktop**.

The current cloud demo is specifically designed to avoid promising any of
these still-unbuilt protections.
