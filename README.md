# EduVision — Vercel Edition

This folder removes Streamlit from the main website.

## Included
- Dark polished EduVision HTML/CSS/JavaScript UI
- School registration + approval workflow
- EduVision Admin login
- School Admin + Teacher login
- Student registration + School Admin approval
- Teacher account management
- Manual attendance with same-day update protection
- Attendance records + reports
- Browser camera access
- Existing Supabase table structure

## Before deploying
1. Open `config.js`.
2. Paste your Supabase project URL.
3. Paste your Supabase **anon/publishable** key.
   - Never paste a `service_role` key into browser code.
4. In Vercel Project Settings → Environment Variables add:
   - `EDUVISION_ADMIN_ID`
   - `EDUVISION_ADMIN_PASSWORD`
5. Import this folder/repository into Vercel and deploy.

## Supabase tables expected
`schools`, `teachers`, `students`, `attendance` with the same columns used by the Streamlit edition.

## Camera AI note
The website camera opens directly in the browser. The old Streamlit/WebRTC code cannot simply run inside HTML.
The included Vercel edition keeps the full school/database/manual-attendance system working, but automatic face identification and YOLO person counting need the trained face assets/model-backed camera services from the current project to be converted separately. Do not delete the working Render version until those two camera AI pieces have been verified on the new deployment.

## Main files
- `index.html` — app entry
- `styles.css` — EduVision UI
- `app.js` — browser application
- `config.js` — Supabase public browser configuration
- `api/admin-login.py` — EduVision Admin login API
- `vercel.json` — Vercel routing
