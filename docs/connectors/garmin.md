# Garmin Connect

The **Garmin Connect** connector links your dashboard directly to the Garmin Cloud API. This allows the application to pull sleep duration, stage segments, heart rate, respiration, body battery change, and overnight HRV statistics.

---

## Configuration Guide

To configure the Garmin Connect connector:

1. Open your web browser and go to the dashboard.
2. Select the **Connectors** tab from the left sidebar navigation.
3. Locate the **Garmin Connect** card.
4. Input your **Garmin Email Address** and your account **Garmin Password**.
5. Check **Enable Auto-Sync** if you want the dashboard to automatically check and download today's sleep metrics in the background once every hour.
6. Click **Save Settings & Credentials**. Once successfully saved, the status badge in the upper right of the card will switch to **Configured** (green).

![Garmin Connect Configuration Card Settings UI](../garmin.png)

---

## Active Data Syncing

You can sync sleep sessions using two different methods:

### 1. Manual Sync
- In the **Trigger Data Sync** section of the card, select a target date using the date picker.
- Click **Run Sync Now**.
- The progress and network calls will stream live logs to the **Synchronization Output Log** console box directly below.
- *Note: Garmin sleep sessions are indexed by their waking morning date. For example, syncing sleep from the night of June 23rd to the morning of June 24th requires selecting date `2026-06-24`.*

### 2. Automated Auto-Sync Daemon
- When **Enable Auto-Sync** is checked and credentials are saved, a background polling worker thread starts on the server.
- Once every hour, the thread checks if a sleep session for "today's morning date" is logged in the database.
- If it is missing, the worker logs into Garmin, checks for a cloud record, and parses/saves the session details.
- To prevent spamming Garmin's endpoints, the sync check is immediately skipped if today's record already exists.

---

## Storage & Pruning Optimization
- To prevent the host server from running out of storage space, the Garmin sync pipeline automatically manages raw payload caches.
- Every time a sync completes, the server scans the storage mount for `garmin_raw_*.json` debug payloads.
- It sorts them and keeps only the **7 most recent files** (one week's archive), automatically deleting older files.
