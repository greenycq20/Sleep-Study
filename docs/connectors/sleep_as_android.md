# Sleep as Android Webhook Connector

The **Sleep as Android Webhook** connector allows the dashboard to ingest real-time sleep tracking states and sound events (snoring, coughing, etc.) directly from your Android device using the popular **Sleep as Android** application.

---

## 1. Webhook Setup & Configuration

To set up the webhook on your phone:

1. Open **Sleep as Android** on your device.
2. Navigate to **Settings** → **Services** → **Automation** → **Webhooks**.
3. Toggle on **Webhooks**.
4. Tap **URL** and enter your self-hosted server's webhook endpoint:
   `http://<your-server-ip>:8000/api/connectors/sleep_as_android/import`
   *(Replace `<your-server-ip>` with the actual IP address or domain name of your dashboard server).*
5. Tap **Events** in the same menu to configure which triggers you wish to send. We recommend enabling:
   - **Sleep tracking started**
   - **Sleep tracking stopped / finished**
   - **Snore / Cough / Talk / Baby crying / Laugh** sound events.

---

## 2. Supported Events & Payload Schema

Every webhook trigger sends an HTTP POST request containing a standard JSON payload:

```json
{
  "event": "event_name",
  "value1": "optional_timestamp_or_metadata",
  "value2": "",
  "value3": ""
}
```

The connector automatically parses these incoming requests. Supported event mappings include:

| Sleep as Android Event | Standardized Metric / Action | Description |
| :--- | :--- | :--- |
| `sleep_tracking_started` | **Session Start** | Initializes or updates the sleep session record. |
| `sleep_tracking_stopped`<br>`sleep_tracking_finished` | **Session End** | Sets the sleep session's final wake time. |
| `sound_event_snore`<br>`snore`<br>`snoring` | **`snore`** | Logs a snoring occurrence. |
| `sound_event_cough`<br>`cough`<br>`coughing` | **`cough`** | Logs a coughing occurrence. |
| `sound_event_talk`<br>`talk` | **`talk`** | Logs talking occurrence. |
| `sound_event_baby`<br>`baby` | **`baby`** | Logs baby crying occurrence. |
| `sound_event_laugh`<br>`laugh` | **`laugh`** | Logs laughter occurrence. |

---

## 3. How the Session Matching Works

Since Sleep as Android events are pushed in real-time throughout the night, the backend uses a deterministic session mapping logic:

1. **Morning Date Calculation**:
   - If an event is received after **12:00 PM (noon)**, it belongs to the sleep session ending the **next morning**.
   - If an event is received before **12:00 PM (noon)**, it belongs to the sleep session ending **this morning**.
2. **Session ID Unification**:
   - The morning date is converted to the format `garmin_YYYYMMDD`.
   - This matches the naming convention used by the Garmin Connect connector, allowing sound events logged by Sleep as Android to merge with your Garmin watch vitals (HRV, stages, resting heart rate) under the same session in your dashboard view.
3. **Time Preserving**:
   - When tracking starts or stops, the session's start/end times are updated.
   - For real-time sound occurrences (like snoring/coughing), the server logs the data sample without modifying the overall sleep period boundaries.
