from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from connectors.base import BaseConnector

class SnoreCoughAppConnector(BaseConnector):
    @property
    def connector_id(self) -> str:
        return "snore_cough_app"

    @property
    def display_name(self) -> str:
        return "Snore & Cough Custom App"

    @property
    def description(self) -> str:
        return "Ingests noise, snoring, and coughing events pushed directly via API/webhook from a custom client app."

    def parse_payload(self, raw_payload: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
        try:
            date_str = raw_payload.get("date")  # YYYY-MM-DD (fallback)
            start_time_str = raw_payload.get("start_time")
            end_time_str = raw_payload.get("end_time")

            if not all([date_str, start_time_str, end_time_str]):
                raise ValueError("Payload missing required session metadata (date, start_time, end_time).")

            # Parse input times
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)

            # 1. Retrieve timezone offset from system settings or environment variable
            import os
            timezone_offset = 0.0
            if db:
                try:
                    from sqlalchemy import and_
                    import database as db_models
                    config_record = db.query(db_models.ConnectorConfig).filter(
                        and_(
                            db_models.ConnectorConfig.connector_id == "system",
                            db_models.ConnectorConfig.config_key == "timezone_offset"
                        )
                    ).first()
                    if config_record:
                        timezone_offset = float(config_record.config_value)
                except Exception as db_err:
                    print(f"[SnoreCoughApp] Error reading timezone_offset from DB: {db_err}")
            
            timezone_offset = float(os.getenv("TIMEZONE_OFFSET", timezone_offset))

            # Helper function to convert ISO string or datetime to UTC naive
            def to_utc_naive(dt: datetime) -> datetime:
                if dt.tzinfo is not None:
                    return dt.astimezone(timedelta(0)).replace(tzinfo=None)
                # Naive is assumed to represent local time; subtract offset to convert to UTC
                return dt - timedelta(hours=timezone_offset)

            # Helper function to convert ISO string or datetime to local naive
            def to_local_naive(dt: datetime) -> datetime:
                if dt.tzinfo is not None:
                    return dt.astimezone(timedelta(hours=timezone_offset)).replace(tzinfo=None)
                # Naive is assumed to represent local time
                return dt

            # 2. Determine local wake time and corresponding morning date
            local_end_time = to_local_naive(end_time)
            morning_date = local_end_time.date().strftime("%Y-%m-%d")

            # 3. Format unified session ID mapping to Garmin format (garmin_YYYYMMDD)
            session_id = f"garmin_{morning_date.replace('-', '')}"

            # 4. Standardize session start/end times in UTC naive
            session_start_utc = to_utc_naive(start_time)
            session_end_utc = to_utc_naive(end_time)

            session_data = {
                "session_id": session_id,
                "date": morning_date,
                "start_time": session_start_utc,
                "end_time": session_end_utc,
            }

            samples = []

            # Parse Snore Events
            snore_events = raw_payload.get("snore_events", [])
            for event in snore_events:
                time_str = event.get("timestamp")
                duration = event.get("duration")
                if time_str:
                    event_dt = datetime.fromisoformat(time_str)
                    samples.append({
                        "metric_type": "snore",
                        "timestamp": to_utc_naive(event_dt),
                        "value_numeric": float(duration) if duration is not None else 1.0,
                        "raw_payload": event
                    })

            # Parse Cough Events
            cough_events = raw_payload.get("cough_events", [])
            for event in cough_events:
                time_str = event.get("timestamp")
                count = event.get("count")
                if time_str:
                    event_dt = datetime.fromisoformat(time_str)
                    samples.append({
                        "metric_type": "cough",
                        "timestamp": to_utc_naive(event_dt),
                        "value_numeric": float(count) if count is not None else 1.0,
                        "raw_payload": event
                    })

            return {
                "session": session_data,
                "samples": samples
            }

        except Exception as e:
            if not isinstance(e, ValueError):
                raise ValueError(f"Failed to parse custom Snore & Cough payload: {str(e)}")
            raise e
