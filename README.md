# English MCQ Test Platform

Full-stack web application for conducting English MCQ tests with admin test creation, automatic question parsing, student test attempts, anti-cheating tab tracking, result dashboards, CSV export, and per-student PDF report.

## Tech Stack

- Frontend: React + Tailwind CSS (`/client`)
- Backend: Flask + SQLite (`/server`)
- Database: local `database.db` file (auto-created)

## Project Structure

- `client/` - React app
- `server/` - Flask API and SQLite logic

## Backend Setup (Flask)

1. Open terminal in `server/`
2. Create virtual environment (recommended):
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Create environment file:
   - Copy `.env.example` to `.env`
5. Run backend:
   - `python app.py`

Backend runs on `http://localhost:5000` by default.

`database.db` is automatically created in `server/` when the app starts.

## Frontend Setup (React + Tailwind)

1. Open terminal in `client/`
2. Install dependencies:
   - `npm install`
3. Create environment file:
   - Copy `.env.example` to `.env`
4. Run frontend:
   - `npm run dev`

Frontend runs on `http://localhost:5173` by default.

## Environment Variables

### Backend (`server/.env`)

- `PORT=5000`
- `CORS_ORIGIN=http://localhost:5173`

### Frontend (`client/.env`)

- `VITE_API_BASE_URL=http://localhost:5000`

## Core Features

### Admin

- Create test (name + duration)
- Paste raw question text and auto-parse into structured questions
- Generate student test link (`/test/{testId}`)
- View submissions dashboard with:
  - Name
  - Registration Number
  - Section
  - Score
  - Tab Switch Count
  - Time Taken
- Export results:
  - CSV (all submissions for test)
  - PDF (per student submission)

### Student (No Login)

- Access test via shared link
- Fill mandatory details:
  - Name
  - Registration Number
  - Section
- Attempt test with countdown timer
- Auto-submit when timer ends
- Tab-switch detection via:
  - `document.visibilitychange`
  - `window.blur`
- Warning shown during test:
  - "Do not switch tabs during the test. Activity is monitored."
- Prevent multiple submissions (server-side check)
- Basic refresh handling using local storage

## API Endpoints

- `GET /api/health`
- `POST /api/tests`
- `GET /api/tests`
- `GET /api/tests/:testId`
- `POST /api/tests/:testId/submit`
- `GET /api/tests/:testId/results`
- `GET /api/tests/:testId/results/export/csv`
- `GET /api/submissions/:submissionId/pdf`

## Deploy Backend on Render

1. Push `server/` code to GitHub
2. In Render, create a new Web Service from repo
3. Configure:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. Set environment variables:
   - `CORS_ORIGIN=https://your-frontend-domain.vercel.app`
   - (Optional) `PORT` is set by Render automatically
5. Deploy

`render.yaml` is included in `server/` as reference.

## Deploy Frontend on Vercel

1. Push `client/` code to GitHub
2. Import project in Vercel
3. Set root directory to `client`
4. Set environment variable:
   - `VITE_API_BASE_URL=https://your-render-backend.onrender.com`
5. Deploy

`vercel.json` is included for SPA route rewrites.

## Notes

- Keep backend and frontend URLs aligned through env variables.
- In production, set strict `CORS_ORIGIN` to your frontend domain (avoid `*`).
