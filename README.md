# Invasive Species Radar

Invasive Species Radar is a local conservation monitoring application. A person uploads a photograph, the server scores it, and the sighting is stored with coordinates. Verified sightings then appear on a map, are grouped with DBSCAN, and can raise early-warning alerts.

The bundled identifier is a real scikit-learn model. It is trained on synthetic colour and texture signatures from a demonstration catalogue. It is a stand-in for a field-trained species model, and it will often return low confidence on ordinary photographs. That low-confidence result is intentional.

## Problem

Conservation teams hear about invasive plants and animals after those species are already established. A shared record of photographs, locations, and verification decisions makes it possible to see a new cluster while it is still small.

## Features

- Citizen, researcher, and administrator accounts with JWT authentication
- Separate plant and animal identification pipelines
- Geotagged sighting submission, with browser location or a map click
- Interactive OpenStreetMap view, marker clustering, and a density grid
- Per-species DBSCAN clustering with the haversine distance
- Alert rules for concentration, growth, a new area, and sensitive regions
- Analytics from stored rows, with rejected reports left out
- Researcher verification and an audit trail
- An editable species catalogue, starting from labelled demonstration entries

## Architecture

```text
Browser (React, Vite, Leaflet, Recharts)
        |  REST + JWT
FastAPI
        |-- auth, sightings, species, verification
        |-- demo or PyTorch identification
        |-- DBSCAN clustering and alert rules
        |-- analytics
SQLite by default, or PostgreSQL + PostGIS
Local image files in backend/uploads
```

Plant and animal classification are separate classes (`PlantClassifier`, `AnimalClassifier`). Both call the configured model and keep only the classes for that category. Object detection is a separate step: OpenCV contours by default, or a local YOLO weights file when `YOLO_WEIGHTS` points at one. Detector labels are not treated as species names.

## Technology

- React, Vite, TypeScript, Tailwind CSS, React Router, Recharts, React Leaflet, Axios
- FastAPI, Pydantic, SQLAlchemy, Alembic
- SQLite for a zero-setup local run
- PostgreSQL and PostGIS when `DATABASE_URL` points at the Docker database
- scikit-learn logistic regression for the demo identifier
- Optional PyTorch and Ultralytics YOLO through `backend/requirements-ml.txt`
- Pillow and OpenCV for image checks and preprocessing
- JWT and bcrypt

## AI workflow

1. Pillow converts the upload to RGB and resizes it. OpenCV applies a small blur when it is installed.
2. The service extracts a fixed colour and texture vector.
3. In demo mode, the plant or animal pipeline scores that vector with the saved logistic regression and compares it with the class centroid.
4. Confidence is the class probability multiplied by a similarity penalty. If the image is far from every training signature, confidence falls below the threshold.
5. A result under the threshold (default 0.45) is stored as unknown and is not linked to a catalogue species.
6. The prediction row stores the model name, version, mode, and the score breakdown.

Demo mode trains itself the first time the model file is missing. Training images are rendered from the catalogue recipes in `backend/app/ai/catalog.py`. Hold-out accuracy is measured on more synthetic signatures, and the model is refused if that accuracy is below 0.90. That number says the model can tell its own recipes apart. It does not measure accuracy on field photographs.

### Replace the demo model

**Keep the demo classifier, retrain it**

```powershell
python ml/training/train_demo_classifier.py
python ml/evaluation/evaluate_demo.py
```

**Train a small PyTorch model on your own folders**

Install `backend/requirements-ml.txt`. Place images in:

```text
ml/datasets/field/<scientific_name>/*.jpg
```

Then run:

```powershell
python ml/training/train_torch_classifier.py
```

Set `INFERENCE_MODE=weights`. The API returns HTTP 503 if that mode is selected and `ml/models/torch_species.pt` or PyTorch is missing. It does not invent a label.

**Use a YOLO detector**

Set `YOLO_WEIGHTS` to a local `.pt` file and install Ultralytics. Detection results are returned by `POST /api/ai/detect` and are labelled as generic detector output.

Score one file from the command line:

```powershell
python ml/inference/predict.py path\to\image.jpg plant
```

## Database

Tables: `users`, `species`, `sightings`, `predictions`, `clusters`, `cluster_sightings`, `alerts`, `verification_records`, `sensitive_regions`, `audit_logs`, `settings`, `model_metadata`.

Sightings store latitude and longitude. On PostgreSQL, startup also enables PostGIS and fills a `geometry(Point, 4326)` column with a GiST index on sightings, clusters, and sensitive regions. Heatmaps and sensitive-region tests use those columns when PostGIS is available. Clustering itself always uses scikit-learn DBSCAN so the same rules run on SQLite and PostgreSQL.

Coordinates are converted to radians. The configured radius in kilometres is divided by the Earth radius (6371.0088 km) to produce the DBSCAN `eps`. Each species is clustered on its own.

Alembic revision `001_initial` creates the SQLAlchemy tables and, on PostgreSQL, the geometry columns.

## API

Interactive docs: `http://127.0.0.1:8000/docs`

| Area | Endpoints |
| --- | --- |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Users | `GET /api/users`, `PUT /api/users/{id}` (administrator) |
| Species | `GET/POST /api/species`, `GET/PUT/DELETE /api/species/{id}` |
| AI | `POST /api/ai/identify`, `POST /api/ai/detect`, `GET /api/ai/model`, `GET /api/ai/samples` |
| Sightings | `POST /api/sightings`, `GET /api/sightings`, `GET/PUT /api/sightings/{id}` |
| Map | `GET /api/map/sightings`, `GET /api/map/clusters`, `GET /api/map/heatmap` |
| Analytics | `GET /api/analytics/overview`, `GET /api/analytics/trends`, `GET /api/analytics/species`, `GET /api/analytics/regions` |
| Clusters | `POST /api/clusters/analyze`, `GET /api/clusters`, `GET /api/clusters/{id}` |
| Alerts | `GET /api/alerts`, `POST /api/alerts/generate`, `PUT /api/alerts/{id}/review` |
| Verification | `GET /api/verification/pending`, `PUT /api/verification/{id}/approve`, `PUT /api/verification/{id}/reject` |
| Settings | `GET /api/settings`, `PUT /api/settings` |
| Health | `GET /api/health` |

List endpoints accept `page` and `page_size`. Sightings and analytics accept species, date, status, and location filters. New registrations are always citizens. Registering cannot grant administrator access.

Official analytics count verified sightings. Rejected sightings are excluded. An administrator can pass `include_unverified=true` to add pending rows. Alert generation uses verified sightings only. A DBSCAN cluster raises an alert only when a size or growth rule is also met.

## Installation

From `invasive-species-radar`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
```

Copy `.env.example` to `.env` when you want to override a setting. The application runs without that file.

### Database setup

The default database is a SQLite file at `backend/invasive_species_radar.db`. The first backend start creates the tables and, if the database has no users, loads the synthetic demonstration set.

Load or rebuild that set yourself with:

```powershell
cd backend
python -m app.database.seed
python -m app.database.seed --reset
```

`--reset` drops the local database and loads the demonstration records again.

PostgreSQL with PostGIS:

```powershell
docker compose up --build
```

The compose file starts PostGIS on port 5432, the API on port 8000, and the Vite app on port 5173. The API URL inside Compose is `postgresql+psycopg://radar:radar@db:5432/invasive_species_radar`.

To point a local API process at that database, set:

```text
DATABASE_URL=postgresql+psycopg://radar:radar@localhost:5432/invasive_species_radar
```

Then run `python -m app.database.seed --reset` from `backend`.

Apply the Alembic revision, if you prefer it to `create_all`:

```powershell
cd backend
alembic upgrade head
```

### Run the backend

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

### Run the frontend

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`.

### Demonstration accounts

These accounts are created by the seed. Passwords are for the local demo only.

| Role | Email | Password |
| --- | --- | --- |
| Citizen | citizen@example.com | DemoCitizen#2026 |
| Researcher | researcher@example.com | DemoResearch#2026 |
| Administrator | admin@example.com | DemoAdmin#2026 |

Every seeded sighting is marked as a synthetic demonstration record. The map and the sighting notes say so. They are not field reports.

The seeded story includes a growing lantana cluster, a water-hyacinth concentration, a snail cluster that is growing but still below the size alert, a small stable cluster that does not alert, an emerging catfish cluster, one mesquite sighting far from the others, and one water-hyacinth point inside a demonstration sensitive region.

## Tests

```powershell
cd backend
python -m pytest
```

The tests cover registration and role limits, invalid images, invalid coordinates, duplicate uploads, low-confidence noise, repeatable demo inference, rejection excluded from analytics, an empty analytics response, species-separated DBSCAN clusters, and bounding-box filtering.

`npm run build` in `frontend` typechecks the interface and produces the production bundle.

## Environment

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | JWT signing key. Required when `ENVIRONMENT=production`. |
| `DATABASE_URL` | SQLAlchemy URL. Defaults to the local SQLite file. |
| `INFERENCE_MODE` | `demo` or `weights`. |
| `MODEL_PATH` | Path to the demo `.joblib` model. |
| `TORCH_WEIGHTS_PATH` | PyTorch checkpoint used in weights mode. |
| `YOLO_WEIGHTS` | Optional local detector weights. |
| `LOW_CONFIDENCE_THRESHOLD` | Default threshold written into settings. |
| `SEED_ON_STARTUP` | Load demonstration data when the user table is empty. |
| `UPLOAD_DIR` | Image directory. |
| `CORS_ORIGINS` | Comma-separated browser origins. |
| `VITE_API_URL` | Optional absolute API URL for a built frontend. The dev server proxies `/api` and `/uploads`. |

## Limitations

- The demo model has not been trained on field photographs. A clear match against a synthetic signature still needs a person to verify it.
- A general YOLO model, if you add one, names everyday object classes. It does not name invasive species.
- Email and SMS delivery are not connected. Alerts are stored and shown in the application so a later notifier can read the same table.
- The local default database is SQLite. Spatial indexes and `ST_DWithin` run when the API is connected to PostgreSQL with PostGIS.
- Demonstration species text is a short educational summary, not a local risk assessment.
