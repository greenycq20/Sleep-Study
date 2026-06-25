# Snore & Cough Custom App (Preview)

The **Snore & Cough Custom App** connector is a custom API listener designed to receive overnight sound event series pushed directly from a secondary recording client (such as a phone, smartwatch app, or microphone hub).

---

## 1. How It Works
- The dashboard starts an API listener endpoint at `/api/connectors/snore_cough_app/import`.
- Client applications make an HTTP POST request sending a JSON payload containing timestamps of snoring durations (seconds) and coughing intervals.
- The dashboard automatically maps these metrics to your Garmin watch session of the corresponding night (by generating a matching deterministic session ID format `garmin_YYYYMMDD` from the morning date). This merges sleep stages, HRV, breathing disruptions, and snoring/coughing timelines on the same charts.

---

## 2. Ingestion API Schema

### Endpoint Details
* **Method**: `POST`
- **URL**: `http://your-server-ip:8000/api/connectors/snore_cough_app/import`
- **Headers**: `Content-Type: application/json`

### Expected JSON Payload Format
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

---

## 3. QR Code App Enrollment
To simplify target IP configuration for custom devices:
1. Navigate to the **Connectors** tab on the dashboard.
2. Under the **Snore & Cough Custom App** card, check the **Scan to Enroll App** QR code block.
3. The QR code dynamically encodes the endpoint JSON metadata using the hostname/IP of the dashboard.
4. Scan the QR code with your client app's scanner to automatically extract and register the endpoint url.
