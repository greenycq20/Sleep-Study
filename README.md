# sleepstudy.app

A self-hosted, offline-first dashboard designed to review, align, and annotate sleep datasets. It combines cloud-synced wellness stats from **Garmin Connect** with custom time-series snoring and coughing metrics pushed from secondary tracking devices or apps.

---

## Key Features

- ⌚ **Garmin Connect Sync**: Sync sleep score, stages (awake, REM, light, deep), resting heart rate, average HRV, body battery dynamics, respiration, and intraday heart rate.
- 🩹 **Sleep Aids Config & Selection**: Manage custom tag lists (e.g. Nose Strips, Mouth Tape, Eye Mask) and log sleep positions (Back, Left Side, Right Side, Stomach) in an interactive sleep journal.
- 🎤 **Snore & Cough Custom App API (Preview)**: A REST API endpoint to ingest sound events from a custom device. Automatically aligns and merges these sounds with your Garmin vitals using deterministic session matching.
- 📱 **QR Code Enrollment**: In-app QR code generation representing your endpoint to instantly auto-configure mobile client applications.
- 🔊 **Sleep as Android Webhook (Preview)**: webhook integration to record real-time audio occurrences.
- 📦 **Dockerized Deployment**: Fully self-contained container packaging for easy hosting on Unraid, Synology, or local homeservers.
- 💾 **Self-Healing Database**: Runs on a local SQLite instance with startup auto-migrations to safely upgrade schemas without data loss.

---

## Workspace Directory Structure

```
sleepstudy.app/
├── docker-dashboard/
│   ├── Dockerfile                  # Container packaging
│   ├── requirements.txt            # Python dependencies
│   ├── main.py                     # API routing and auto-sync worker
│   ├── config.py                   # Storage directories config
│   ├── database.py                 # SQLite models & migrations
│   ├── crud.py                     # Database CRUD transactions
│   ├── connector_manager.py        # Connectors acquisition framework
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── base.py                 # Connector interface
│   │   ├── garmin.py               # Garmin cloud fetcher & pruner
│   │   ├── health_connect.py       # Health Connect backup importer
│   │   └── snore_cough_app.py      # Custom push listener
│   └── static/
│       ├── index.html              # HTML structure with cache-busters
│       ├── style.css               # Glassmorphic styling
│       ├── app.js                  # Frontend interactions & rendering
│       └── qrious.min.js           # QR Code generator library
│
└── mock-data-sources/              # Example JSON files for manual import
```

---

## Deployment & Setup

### 1. Build the Docker Image
Run the build command in the root folder of the project:
```bash
docker build -t sleepstudy-app:latest ./docker-dashboard
```

### 2. Run the Container
Launch the container. Map a local directory to preserve the database (`sleep_study.db`) and Garmin cached session tokens:
```bash
docker run -d \
  --name sleep-study-dashboard \
  -p 8000:8000 \
  -v /path/to/your/local/data:/app/data \
  sleepstudy-app:latest
```

Open your browser and navigate to `http://localhost:8000/`.

---

## API Endpoints & Webhooks

### 1. Snore & Cough Custom App Ingestion (Preview)
- **Endpoint**: `POST /api/connectors/snore_cough_app/import`
- **Headers**: `Content-Type: application/json`
- **Expected Payload JSON Format**:
  ```json
  {
    "date": "2026-06-25",
    "start_time": "2026-06-24T22:30:00",
    "end_time": "2026-06-25T06:45:00",
    "snore_events": [
      { "timestamp": "2026-06-25T01:15:22", "duration": 18 }
    ],
    "cough_events": [
      { "timestamp": "2026-06-25T02:30:15", "count": 2 }
    ]
  }
  ```

### 2. Sleep as Android Webhook (Preview)
- **Endpoint**: `POST /api/connectors/sleep_as_android/import`
- **Webhook Configuration**: Enable webhook settings inside the Sleep as Android app (under Services → Automation → Webhooks) and point to the above URL.

---

## Storage & Auto-Sync Configuration

### Garmin Auto-Sync
Inside the dashboard settings under **Connectors**, input your Garmin credentials and enable **Auto-Sync**. 
- A background worker thread checks once every hour to see if today's morning sleep is in the database.
- If missing, it fetches the sleep window and intraday heart rate/vitals.
- To avoid rate-limits, it skips checks if today's record already exists.

### Automatic Payload Cleanup
To prevent running out of storage space on thin local hosts or servers:
- The Garmin Connect sync automatically scans the directory for debug file caches (`garmin_raw_*.json`).
- It prunes older files, keeping only a rolling **7-day archive** (one week of raw API payloads) on disk.
