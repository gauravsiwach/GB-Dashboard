# GB Dashboard — Monorepo Scaffold

This repository contains a minimal scaffold for the GB Dashboard project.

Structure:
- `api/` — FastAPI backend
- `web/` — React frontend (Vite)

Prerequisites
- Python 3.11+ and `npm` / Node.js installed

Backend (API)

Create and activate a virtual environment, install dependencies, and run the API:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
uvicorn api.app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000` and the health endpoint at `http://127.0.0.1:8000/health`.

Frontend (Web)

Install frontend dependencies and start the Vite dev server:

```bash
cd web
npm install
npm run dev
```

By default Vite serves the app at `http://localhost:5173` (check terminal output). The example app calls the backend `/health` endpoint; if running both locally you may need to run the backend on port `8000` as shown above.

Running both services concurrently

Open two terminals. In one, run the backend (see Backend commands). In the other, run the frontend (see Frontend commands).

See `api/README.md` and `web/README.md` for more details on tests and development.

