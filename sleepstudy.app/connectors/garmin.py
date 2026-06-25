import os
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

import config
import crud
from connectors.base import BaseConnector

class GarminConnector(BaseConnector):
    @property
    def connector_id(self) -> str:
        return "garmin"

    @property
    def display_name(self) -> str:
        return "Garmin Connect"

    @property
    def description(self) -> str:
        return "Ingests sleep periods, stages, heart rate, and respiration directly from Garmin data."

    def fetch_data(self, db: Session, date_str: str, log_callback=None) -> Dict[str, Any]:
        """
        Actively login and fetch sleep data for the requested date from Garmin Connect API.
        Retrieves sleep summary, sleep levels, respiration, and intraday heart rate.
        """
        def log(msg):
            if log_callback:
                log_callback(f"[Garmin Sync] {msg}\n")
            print(f"[Garmin Sync] {msg}")

        # 1. Load Garmin credentials from database
        configs = crud.get_connector_config(db, self.connector_id)
        email = configs.get("email")
        password = configs.get("password")

        if not email or not password:
            log("ERROR: Credentials not configured. Please save your Garmin Connect email and password first.")
            raise ValueError("Garmin credentials are not configured in settings.")

        # 2. Login utilizing token caching to avoid rate-limits
        tokenstore_path = os.path.join(config.DATA_DIR, "garmin_tokens")
        os.makedirs(tokenstore_path, exist_ok=True)

        log(f"Authenticating with Garmin Connect for account: {email}...")
        try:
            from garminconnect import Garmin
            client = Garmin(email, password)
            
            oauth1_file = os.path.join(tokenstore_path, "oauth1_token.json")
            if os.path.exists(oauth1_file):
                log("Found cached session tokens. Attempting to resume session...")
                try:
                    client.login(tokenstore=tokenstore_path)
                    log("Session resumed successfully from cache.")
                except Exception as resume_err:
                    log(f"Cached session invalid ({resume_err}). Performing fresh login...")
                    client.login()
                    client.garth.dump(tokenstore_path)
                    log("Fresh login successful. Session tokens updated.")
            else:
                log("No cached session tokens found. Performing initial login...")
                client.login()
                client.garth.dump(tokenstore_path)
                log("Initial login successful. Session tokens saved.")
        except Exception as e:
            log(f"ERROR: Authentication failed: {e}")
            raise RuntimeError(f"Garmin Connect login failed: {e}")

        # 3. Retrieve Sleep data for the target date
        log(f"Fetching sleep data for morning date {date_str}...")
        try:
            sleep_data = client.get_sleep_data(date_str)
            if not sleep_data or "dailySleepDTO" not in sleep_data:
                log(f"WARNING: No sleep record found on Garmin Connect for the morning of {date_str}.")
                return {"session": None, "samples": []}
            log("Retrieved sleep stages and summary successfully.")
            
            # Save raw JSON for debugging/inspection in persistent data directory
            import json
            debug_file = os.path.join(config.DATA_DIR, f"garmin_raw_{date_str}.json")
            try:
                with open(debug_file, "w") as f:
                    json.dump(sleep_data, f, indent=2)
                log(f"Saved raw Garmin API sleep response to persistent file: data/garmin_raw_{date_str}.json")
                
                # Perform cleanup of old raw payloads (keep only the 7 most recent files)
                import glob
                raw_files = glob.glob(os.path.join(config.DATA_DIR, "garmin_raw_*.json"))
                # Sorting alphabetically sorts chronologically since the filename includes YYYY-MM-DD
                raw_files.sort()
                
                if len(raw_files) > 7:
                    files_to_delete = raw_files[:-7]
                    for f_to_del in files_to_delete:
                        try:
                            os.remove(f_to_del)
                            log(f"Cleaned up old raw Garmin payload file: {os.path.basename(f_to_del)}")
                        except Exception as del_err:
                            log(f"WARNING: Could not delete old raw file {f_to_del}: {del_err}")
                            
            except Exception as debug_err:
                log(f"WARNING: Could not write debug payload: {debug_err}")
        except Exception as e:
            log(f"ERROR: Failed to retrieve sleep data: {e}")
            raise RuntimeError(f"Failed to fetch sleep data from Garmin Connect: {e}")

        # 4. Extract Sleep session window to fetch matching intraday heart rate
        dto = sleep_data["dailySleepDTO"]
        start_ms = dto.get("sleepStartTimestampGMT") or dto.get("sleepStartTimestampLocal")
        end_ms = dto.get("sleepEndTimestampGMT") or dto.get("sleepEndTimestampLocal")

        heart_rates_list = []
        if start_ms and end_ms:
            # Sleep target is date_str (wake morning). Sleep onset occurred the previous calendar day.
            from datetime import timedelta
            target_date = datetime.fromisoformat(date_str).date()
            start_date_str = (target_date - timedelta(days=1)).isoformat()
            end_date_str = date_str
            
            log(f"Sleep window (UTC): {datetime.utcfromtimestamp(start_ms / 1000).isoformat()} to {datetime.utcfromtimestamp(end_ms / 1000).isoformat()}")
            
            # Fetch heart rates for both dates to fully cover the sleep window crossing midnight
            log(f"Fetching daily heart rates for {start_date_str} and {end_date_str}...")
            try:
                dates_to_fetch = list(set([start_date_str, end_date_str]))
                all_hr_values = []
                for d in dates_to_fetch:
                    hr_response = client.get_heart_rates(d)
                    if hr_response and "heartRateValues" in hr_response:
                        all_hr_values.extend(hr_response["heartRateValues"])
                
                # Filter heart rates within the sleep window
                for hr_point in all_hr_values:
                    # Format is [timestamp_ms, hr_bpm]
                    if len(hr_point) >= 2:
                        ts_ms, bpm = hr_point[0], hr_point[1]
                        if ts_ms and bpm and start_ms <= ts_ms <= end_ms:
                            heart_rates_list.append({
                                "time": datetime.fromtimestamp(ts_ms / 1000).isoformat(),
                                "hr": bpm
                            })
                log(f"Filtered {len(heart_rates_list)} heart rate samples for the sleep session.")
            except Exception as e:
                log(f"WARNING: Could not fetch heart rate details: {e}")
        else:
            log("WARNING: Could not determine sleep window timestamps. Skipping heart rates.")

        # 5. Pack into raw payload for unified parser
        combined_payload = {
            "session_id": f"garmin_{date_str.replace('-', '')}",
            "date": date_str,
            "api_response": sleep_data,
            "api_heart_rates": heart_rates_list
        }

        # 6. Parse and return standard dataset format
        return self.parse_payload(combined_payload)

    def parse_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Check if this is the official Garmin Connect API response structure
            if "api_response" in raw_payload:
                return self._parse_official_api(raw_payload)
            elif "dailySleepDTO" in raw_payload:
                # Direct manual import of official raw Garmin JSON payload
                dto = raw_payload["dailySleepDTO"]
                date_str = dto.get("calendarDate")
                wrapped = {
                    "session_id": f"garmin_{date_str.replace('-', '')}",
                    "date": date_str,
                    "api_response": raw_payload,
                    "api_heart_rates": []  # Will fall back to sleepHeartRate inside _parse_official_api
                }
                return self._parse_official_api(wrapped)
            else:
                # Fallback to standard mock importer format (Phase 3 format)
                return self._parse_mock_format(raw_payload)

        except Exception as e:
            if not isinstance(e, ValueError):
                raise ValueError(f"Failed to parse Garmin payload: {str(e)}")
            raise e

    def _parse_official_api(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        api_response = raw_payload["api_response"]
        session_id = raw_payload["session_id"]
        date_str = raw_payload["date"]
        api_heart_rates = raw_payload.get("api_heart_rates", [])

        dto = api_response["dailySleepDTO"]
        start_ms = dto.get("sleepStartTimestampGMT") or dto.get("sleepStartTimestampLocal")
        end_ms = dto.get("sleepEndTimestampGMT") or dto.get("sleepEndTimestampLocal")

        if not start_ms or not end_ms:
            raise ValueError("Garmin sleep API response missing start/end timestamps.")

        start_time = datetime.fromtimestamp(start_ms / 1000)
        end_time = datetime.fromtimestamp(end_ms / 1000)

        # Parse sleep score
        sleep_score = None
        score_obj = dto.get("overallSleepScore")
        if isinstance(score_obj, dict):
            sleep_score = score_obj.get("value")
        elif score_obj is not None:
            sleep_score = score_obj
        else:
            sleep_score = dto.get("sleepScore")

        session_data = {
            "session_id": session_id,
            "date": date_str,
            "start_time": start_time,
            "end_time": end_time,
            "sleep_score": int(sleep_score) if sleep_score is not None else None,
            "resting_heart_rate": int(api_response.get("restingHeartRate")) if api_response.get("restingHeartRate") is not None else None,
            "avg_overnight_hrv": int(api_response.get("avgOvernightHrv")) if api_response.get("avgOvernightHrv") is not None else None,
            "hrv_status": api_response.get("hrvStatus"),
            "body_battery_change": int(api_response.get("bodyBatteryChange")) if api_response.get("bodyBatteryChange") is not None else None,
        }

        samples = []

        # 1. Parse Sleep Stages (sleepLevels)
        # Mapping: 0 = awake, 1 = light, 2 = deep, 3 = rem
        STAGE_MAPPING = {
            0: "awake",
            1: "light",
            2: "deep",
            3: "rem"
        }
        
        sleep_levels = api_response.get("sleepLevels", [])
        for level_segment in sleep_levels:
            lvl_val = level_segment.get("activityLevel")
            st_str = level_segment.get("startGMT")
            et_str = level_segment.get("endGMT")

            # Normalise time strings (replace space with T for ISO format parsing)
            if st_str: st_str = st_str.replace(" ", "T")
            if et_str: et_str = et_str.replace(" ", "T")

            stage_name = STAGE_MAPPING.get(lvl_val)
            if stage_name and st_str:
                samples.append({
                    "metric_type": "sleep_stage",
                    "timestamp": datetime.fromisoformat(st_str),
                    "value_text": stage_name,
                    "raw_payload": {
                        "stage": stage_name,
                        "startTime": st_str,
                        "endTime": et_str
                    }
                })

        # 2. Parse Heart Rate series
        if api_heart_rates:
            for hr_point in api_heart_rates:
                samples.append({
                    "metric_type": "heart_rate",
                    "timestamp": datetime.fromisoformat(hr_point["time"]),
                    "value_numeric": float(hr_point["hr"]),
                    "raw_payload": hr_point
                })
        else:
            # Fallback to sleepHeartRate inside the main API sleep response (contains overnight samples)
            sleep_hr = api_response.get("sleepHeartRate", []) or []
            for hr_point in sleep_hr:
                ts_ms = hr_point.get("startGMT")
                hr_val = hr_point.get("value")
                if ts_ms and hr_val is not None:
                    samples.append({
                        "metric_type": "heart_rate",
                        "timestamp": datetime.fromtimestamp(ts_ms / 1000),
                        "value_numeric": float(hr_val),
                        "raw_payload": hr_point
                    })

        # 3. Parse Respiration series
        resp_list = api_response.get("wellnessEpochRespirationDataDTOList", []) or []
        for resp_point in resp_list:
            resp_start = resp_point.get("startTimeGMT")
            resp_val = resp_point.get("respirationValue") or resp_point.get("respirationRate")
            if resp_start and resp_val is not None:
                if isinstance(resp_start, (int, float)):
                    ts = datetime.fromtimestamp(resp_start / 1000)
                else:
                    ts = datetime.fromisoformat(str(resp_start).replace(" ", "T"))
                
                samples.append({
                    "metric_type": "respiration",
                    "timestamp": ts,
                    "value_numeric": float(resp_val),
                    "raw_payload": resp_point
                })

        # 4. Parse SpO2 series
        spo2_list = api_response.get("wellnessEpochSPO2DataDTOList", []) or []
        for spo2_point in spo2_list:
            ts_val = spo2_point.get("epochTimestamp") or spo2_point.get("startTimeGMT")
            spo2_val = spo2_point.get("spo2Reading") or spo2_point.get("spo2Value")
            if ts_val and spo2_val is not None:
                if isinstance(ts_val, (int, float)):
                    ts = datetime.fromtimestamp(ts_val / 1000)
                else:
                    ts = datetime.fromisoformat(str(ts_val).replace(" ", "T"))
                
                samples.append({
                    "metric_type": "spo2",
                    "timestamp": ts,
                    "value_numeric": float(spo2_val),
                    "raw_payload": spo2_point
                })

        # 5. Parse Stress series
        stress_list = api_response.get("sleepStress", []) or []
        for stress_point in stress_list:
            ts_ms = stress_point.get("startGMT")
            stress_val = stress_point.get("value")
            if ts_ms and stress_val is not None:
                samples.append({
                    "metric_type": "stress",
                    "timestamp": datetime.fromtimestamp(ts_ms / 1000),
                    "value_numeric": float(stress_val),
                    "raw_payload": stress_point
                })

        # 6. Parse Body Battery series
        bb_list = api_response.get("sleepBodyBattery", []) or []
        for bb_point in bb_list:
            ts_ms = bb_point.get("startGMT")
            bb_val = bb_point.get("value")
            if ts_ms and bb_val is not None:
                samples.append({
                    "metric_type": "body_battery",
                    "timestamp": datetime.fromtimestamp(ts_ms / 1000),
                    "value_numeric": float(bb_val),
                    "raw_payload": bb_point
                })

        # 7. Parse HRV series
        hrv_list = api_response.get("hrvData", []) or []
        for hrv_point in hrv_list:
            ts_ms = hrv_point.get("startGMT")
            hrv_val = hrv_point.get("value")
            if ts_ms and hrv_val is not None:
                samples.append({
                    "metric_type": "hrv",
                    "timestamp": datetime.fromtimestamp(ts_ms / 1000),
                    "value_numeric": float(hrv_val),
                    "raw_payload": hrv_point
                })

        # 8. Parse Breathing Disruptions series
        bd_list = api_response.get("breathingDisruptionData", []) or []
        for bd_point in bd_list:
            ts_ms = bd_point.get("startGMT") or bd_point.get("startTimeGMT")
            bd_val = bd_point.get("value")
            if ts_ms and bd_val is not None:
                samples.append({
                    "metric_type": "breathing_disruption",
                    "timestamp": datetime.fromtimestamp(ts_ms / 1000),
                    "value_numeric": float(bd_val),
                    "raw_payload": bd_point
                })

        return {
            "session": session_data,
            "samples": samples
        }

    def _parse_mock_format(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        session_id = raw_payload.get("session_id")
        date_str = raw_payload.get("date")
        sleep_onset_str = raw_payload.get("sleepOnset")
        sleep_offset_str = raw_payload.get("sleepOffset")
        
        if not all([session_id, date_str, sleep_onset_str, sleep_offset_str]):
            raise ValueError("Garmin payload missing required session metadata (session_id, date, sleepOnset, sleepOffset).")

        start_time = datetime.fromisoformat(sleep_onset_str)
        end_time = datetime.fromisoformat(sleep_offset_str)
        sleep_score = raw_payload.get("sleepScore")

        session_data = {
            "session_id": session_id,
            "date": date_str,
            "start_time": start_time,
            "end_time": end_time,
            "sleep_score": int(sleep_score) if sleep_score is not None else None
        }

        samples = []

        stages = raw_payload.get("sleepStages", [])
        for stage in stages:
            stage_type = stage.get("stage")
            st_str = stage.get("startTime")
            et_str = stage.get("endTime")
            if stage_type and st_str:
                samples.append({
                    "metric_type": "sleep_stage",
                    "timestamp": datetime.fromisoformat(st_str),
                    "value_text": stage_type,
                    "raw_payload": stage
                })

        hr_series = raw_payload.get("heartRateSeries", [])
        for hr_point in hr_series:
            time_str = hr_point.get("time")
            hr_val = hr_point.get("hr")
            if time_str and hr_val is not None:
                samples.append({
                    "metric_type": "heart_rate",
                    "timestamp": datetime.fromisoformat(time_str),
                    "value_numeric": float(hr_val),
                    "raw_payload": hr_point
                })

        br_series = raw_payload.get("respirationSeries", [])
        for br_point in br_series:
            time_str = br_point.get("time")
            br_val = br_point.get("br")
            if time_str and br_val is not None:
                samples.append({
                    "metric_type": "respiration",
                    "timestamp": datetime.fromisoformat(time_str),
                    "value_numeric": float(br_val),
                    "raw_payload": br_point
                })

        return {
            "session": session_data,
            "samples": samples
        }
