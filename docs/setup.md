# Installation & Setup

This guide walks you through building, configuring, and deploying `sleepstudy.app` inside a Docker container.

---

## 1. Prerequisites
Ensure you have Docker installed on your host server (e.g. Unraid, Synology, Ubuntu, or Windows/macOS with Docker Desktop).

---

## 2. Docker Deployment

### A. Build the Image Locally
Clone the repository, navigate to the project directory, and run the Docker build command:
```bash
docker build -t sleepstudy-app:latest ./sleepstudy.app
```

### B. Run the Container
Start the container with a local volume bind-mounted to preserve your metrics database and Garmin Connect tokens:
```bash
docker run -d \
  --name sleep-study-dashboard \
  -p 8000:8000 \
  -v /mnt/user/appdata/sleepstudy:/app/data \
  sleepstudy-app:latest
```

* **`-p 8000:8000`**: Maps port 8000 to access the UI on your network.
* **`-v /app/data`**: Map this folder to a persistent directory on your host. This ensures your configurations and database are not lost when rebuilding or updating the container.

### C. Docker Dashboard / Unraid Custom Icon
For platforms that support custom container icons (such as Unraid templates or custom dashboards), use the following hosted URL:
* **Icon URL**: `https://raw.githubusercontent.com/greenycq20/Sleep-Study/main/docs/logo.png`

---

## 3. Database & Storage Architecture

The dashboard database uses a single **SQLite** file.
* **Database File Location**: `/app/data/sleep_study.db` (in the container volume).
- **Self-Healing Schema Migrations**: The database executes auto-migrations on application startup inside `init_db()`. If you upgrade the container to a version that requires new tables or columns, the backend applies `ALTER TABLE` commands dynamically, preserving your existing notes and ratings data.

### Table Schema Models

1. **`sleep_sessions`**:
   - `id` (String): Session ID (e.g., `garmin_YYYYMMDD`).
   - `date` (String): Target morning date.
   - `start_time` (DateTime): Sleep onset.
   - `end_time` (DateTime): Wake onset.
   - `rating` (Integer): Quality rating (1 to 5 stars).
   - `notes` (String): Annotation text.
   - `sleep_score` (Integer): Overall score (0-100).
   - `resting_heart_rate` (Integer): Garmin resting HR.
   - `avg_overnight_hrv` (Integer): Garmin average overnight HRV.
   - `hrv_status` (String): Garmin HRV status description.
   - `body_battery_change` (Integer): Net change in body battery.
   - `sleep_position` (String): Logged sleep position.
   - `sleep_aids` (String): Comma-separated list of sleep aid tags.

2. **`sleep_metric_samples`**:
   - `id` (Integer): Auto-increment primary key.
   - `session_id` (String): Foreign key referencing `sleep_sessions`.
   - `connector_id` (String): Source connector (e.g. `garmin`, `snore_cough_app`).
   - `metric_type` (String): Metric type (e.g. `sleep_stage`, `heart_rate`, `respiration`, `snore`, `cough`, `spo2`, `stress`, `body_battery`, `hrv`, `breathing_disruption`).
   - `timestamp` (DateTime): Measurement timestamp.
   - `value_numeric` (Float): Value for continuous datasets (e.g. BPM, breathing disruptions).
   - `value_text` (String): Value for categorical datasets (e.g. deep, light sleep).
   - `raw_payload` (String): JSON serialization of the original point.

3. **`sleep_aids`**:
   - `id` (Integer): Primary key.
   - `name` (String): Custom tag name (e.g. `Nose Strips`).

4. **`connector_configs`**:
   - `connector_id` (String): e.g. `garmin`.
   - `config_key` (String): e.g. `email`.
   - `config_value` (String): Config value.
