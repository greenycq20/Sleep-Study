from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from connectors.base import BaseConnector

class HealthConnectConnector(BaseConnector):
    @property
    def connector_id(self) -> str:
        return "health_connect"

    @property
    def display_name(self) -> str:
        return "Google Health Connect"

    @property
    def description(self) -> str:
        return "Ingests sleep, heart rate, oxygen saturation, and noise event logs (snore, cough) synced from Android devices."

    def parse_payload(self, raw_payload: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
        try:
            # Validate core fields
            session_id = raw_payload.get("session_id")
            date_str = raw_payload.get("date")  # YYYY-MM-DD
            start_time_str = raw_payload.get("start_time")
            end_time_str = raw_payload.get("end_time")

            if not all([session_id, date_str, start_time_str, end_time_str]):
                raise ValueError("Health Connect payload missing required session metadata (session_id, date, start_time, end_time).")

            # Parse datetimes
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
            sleep_score = raw_payload.get("sleep_score")

            session_data = {
                "session_id": session_id,
                "date": date_str,
                "start_time": start_time,
                "end_time": end_time,
                "sleep_score": int(sleep_score) if sleep_score is not None else None
            }

            samples = []

            # 1. Parse Sleep Stages
            stages = raw_payload.get("stages", [])
            for stage in stages:
                stage_type = stage.get("stage_type")  # light, deep, rem, awake
                st_str = stage.get("start")
                et_str = stage.get("end")
                if stage_type and st_str:
                    samples.append({
                        "metric_type": "sleep_stage",
                        "timestamp": datetime.fromisoformat(st_str),
                        "value_text": stage_type,
                        "raw_payload": stage
                    })

            # 2. Parse Heart Rate Series
            hr_series = raw_payload.get("heart_rate", [])
            for hr_point in hr_series:
                time_str = hr_point.get("timestamp")
                hr_val = hr_point.get("bpm")
                if time_str and hr_val is not None:
                    samples.append({
                        "metric_type": "heart_rate",
                        "timestamp": datetime.fromisoformat(time_str),
                        "value_numeric": float(hr_val),
                        "raw_payload": hr_point
                    })

            # 3. Parse Snore Events
            snore_events = raw_payload.get("snore_events", [])
            for event in snore_events:
                time_str = event.get("timestamp")
                duration = event.get("duration")  # duration in seconds
                if time_str:
                    samples.append({
                        "metric_type": "snore",
                        "timestamp": datetime.fromisoformat(time_str),
                        "value_numeric": float(duration) if duration is not None else 1.0,
                        "raw_payload": event
                    })

            # 4. Parse Cough Events
            cough_events = raw_payload.get("cough_events", [])
            for event in cough_events:
                time_str = event.get("timestamp")
                count = event.get("count")  # count in interval
                if time_str:
                    samples.append({
                        "metric_type": "cough",
                        "timestamp": datetime.fromisoformat(time_str),
                        "value_numeric": float(count) if count is not None else 1.0,
                        "raw_payload": event
                    })

            return {
                "session": session_data,
                "samples": samples
            }

        except Exception as e:
            if not isinstance(e, ValueError):
                raise ValueError(f"Failed to parse Health Connect payload: {str(e)}")
            raise e
