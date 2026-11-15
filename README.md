# Lunar Landing Site Navigator 🌕

**2026 NASA Space Apps Challenge** | Team: **codeTooworst**

An interactive web application that helps mission planners, scientists, and educators rapidly evaluate and compare lunar landing sites—especially at the Moon’s South Pole. It translates complex ephemeris and topographic data into clear visualizations of Sun and Earth positions, power generation potential, and Direct-to-Earth (DTE) communication windows.

## 🚀 Key Features

- **Landing Site Selection:** Curated lunar landing-site presets (South Pole targets, Apollo, CLPS) plus custom latitude/longitude input.
- **Flexible Mission Timeline:** Customizable mission start date, duration, and ephemeris sample-step controls.
- **Polar Sky Plot:** Real-time visualization of Sun and Earth azimuth and elevation relative to the horizon.
- **Time-Scrubbable Timeline:** Interactive timeline showing illumination periods and Direct-to-Earth communication windows.
- **Mission Metrics & Charts:** Automated suitability scoring, solar elevation charts, and countdowns to sunset/Earthset.
- **Side-by-Side Comparison:** Compare multiple candidate sites or shifted launch dates simultaneously.
- **Data Export:** One-click CSV export of the returned ephemeris time series.

## 🛠 Tech Stack & NASA Data

- **Frontend:** React, TypeScript, Vite (`frontend/`)
- **Backend:** Python 3.11+, FastAPI (`app/`)
- **NASA Resources Referenced:** JPL Horizons System (ephemerides), Moon Trek / LOLA (lunar topography), and LRO Quickmap.

---

## ⚙️ Local Setup & Run

### 1. Start the Backend (FastAPI)

Requires **Python 3.11+**:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000` (interactive API docs at `/docs`).

### 2. Start the Frontend (React + Vite)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`). The frontend uses `VITE_API_URL` (defaults to `http://127.0.0.1:8000`). Copy `frontend/.env.example` to `frontend/.env` only if you need to override the API URL.
