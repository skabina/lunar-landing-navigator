# Lunar Landing Site Navigator — Frontend v2

A responsive mission-planning interface for comparing lunar landing candidates, local solar illumination and direct-to-Earth visibility.

## Run locally

1. Install Node.js 20+.
2. Install dependencies: `npm install`
3. Start the API backend (FastAPI) on `http://127.0.0.1:8000`.
4. Start the frontend: `npm run dev`

Set `VITE_API_URL` in `.env` if the API is hosted elsewhere. The frontend expects:
- `GET /api/v1/presets`
- `POST /api/v1/analyze-site`
- `POST /api/v1/compare`

## Included

- Responsive mission parameter panel and curated/custom coordinates
- Sun/Earth polar horizon view and sample-by-sample timeline scrubber
- Illumination, communication and joint-operation metrics
- Suitability breakdown, elevation chart, data provenance/warnings
- Two-scenario comparison and CSV ephemeris export

## Scientific limitations

This UI presents the backend's returned values and warnings. A score is a heuristic decision-support indicator, not a certified mission feasibility assessment. If the API reports fallback ephemeris or a reference horizon, the UI labels that source; it does not imply validated NASA Horizons or DEM-derived terrain data.
