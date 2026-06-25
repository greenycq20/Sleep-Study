# Data Connectors

`sleepstudy.app` supports multiple pathways to ingest sleep periods, sleep stages, and time-series vitals or noise metrics. 

Refer to the individual connector guides below for detailed instructions, credentials setups, API specifications, and JSON payload formats:

---

## Available Connectors

### 1. ⌚ [Garmin Connect](connectors/garmin.md)
*Cloud Sync Integration*
Fetch overnight sleep segments, sleep score, resting heart rate, average HRV, body battery dynamics, respiration epoch metrics, stress levels, and SpO2. Features hourly background auto-sync daemon checking and auto-pruning cache optimization.

### 2. 🎤 [Snore & Cough Custom App (Preview)](connectors/snore_cough_app.md)
*Custom API Integration*
An HTTP POST listener endpoint designed to receive time-series snoring and coughing sound events pushed from a microphone client. Includes dynamic QR Code app enrollment configurations.

### 3. 🔊 [Sleep as Android Webhook (Preview)](connectors/sleep_as_android.md)
*Webhook Integration*
Ingests webhook event streams pushed automatically from the Sleep as Android app automation settings.
