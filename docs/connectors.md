# Data Connectors

`sleepstudy.app` features a modular connectors architecture to ingest sleep statistics and time-series physiological metrics. There are currently three connectors implemented:

---

## 1. Garmin Connect

Connects to Garmin cloud to sync sleep periods and vitals tracked by your Garmin smartwatch.

### Features
* **Full Stage Resolution**: Imports sleep intervals (Awake, REM, Light, Deep).
- **Physiological Vitals**: Overnight heart rate, average HRV, HRV status, Body Battery change, epoch respiration, stress, and oxygen saturation (SpO2).
- **Hourly Auto-Sync**: Automatically checks if today's sleep session is present in the database. If missing, it queries Garmin's API.
- **Storage Optimization**: Automatically prunes raw Garmin API caches (`garmin_raw_*.json`) in the data directory, keeping only the 7 most recent days of files to prevent host system disk exhaustion.

### Credentials Setup
Save your Garmin credentials in the settings dashboard:
* **Garmin Email**: Your Garmin Connect account email.
* **Garmin Password**: Your account password.
* **Auto-Sync**: Check to enable hourly background sync daemon thread.

---

## 2. Snore & Cough Custom App (Preview)

A custom HTTP POST API listener endpoint designed to ingest overnight sound events (snoring duration and coughing count) recorded by a secondary microphone client.

### Endpoints
* **URL**: `POST /api/connectors/snore_cough_app/import`
- **Session Merging**: paylaod is matched to the corresponding Garmin watch session of the same night by using the deterministic format `garmin_YYYYMMDD` (representing the morning date). If no Garmin watch data exists, a session container is still created to view sound events.
- **Expected JSON Payload Format**:
  ```json
  {
    "date": "2026-06-25",
    "start_time": "2026-06-24T22:30:00",
    "end_time": "2026-06-25T06:45:00",
    "snore_events": [
      {
        "timestamp": "2026-06-25T01:15:22",
        "duration": 18
      },
      {
        "timestamp": "2026-06-25T03:42:10",
        "duration": 5
      }
    ],
    "cough_events": [
      {
        "timestamp": "2026-06-25T02:30:15",
        "count": 2
      }
    ]
  }
  ```

### App Enrollment QR Code
To streamline enrollment, the dashboard displays a scan configuration QR Code inside settings. It encodes:
```json
{
  "connector_id": "snore_cough_app",
  "endpoint_url": "http://your-server-ip:8000/api/connectors/snore_cough_app/import"
}
```
Client applications can scan this to auto-configure their endpoint destinations.

---

## 3. Sleep as Android Webhook (Preview)

Allows real-time logging of audio events using Webhooks from the Sleep as Android automation suite.

### Webhook Configuration
1. Open settings in **Sleep as Android**.
2. Go to **Services** → **Automation** → **Webhooks**.
3. Enable webhooks and input the dashboard endpoint:
   `http://your-server-ip:8000/api/connectors/sleep_as_android/import`
4. The mobile app will post events dynamically as they occur during sleep.
