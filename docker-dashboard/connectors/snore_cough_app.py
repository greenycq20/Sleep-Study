from datetime import datetime
from typing import Dict, Any
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

    def parse_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            date_str = raw_payload.get("date")  # YYYY-MM-DD
            start_time_str = raw_payload.get("start_time")
            end_time_str = raw_payload.get("end_time")

            if not all([date_str, start_time_str, end_time_str]):
                raise ValueError("Payload missing required session metadata (date, start_time, end_time).")

            # Validate date format (YYYY-MM-DD)
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError("date must be in YYYY-MM-DD format.")

            # Parse times to validate format
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)

            # We format the session_id to match the Garmin format: garmin_YYYYMMDD
            # This ensures that custom app events merge seamlessly under the same sleep session in the UI.
            session_id = f"garmin_{date_str.replace('-', '')}"

            session_data = {
                "session_id": session_id,
                "date": date_str,
                "start_time": start_time,
                "end_time": end_time,
            }

            samples = []

            # Parse Snore Events
            snore_events = raw_payload.get("snore_events", [])
            for event in snore_events:
                time_str = event.get("timestamp")
                duration = event.get("duration")
                if time_str:
                    samples.append({
                        "metric_type": "snore",
                        "timestamp": datetime.fromisoformat(time_str),
                        "value_numeric": float(duration) if duration is not None else 1.0,
                        "raw_payload": event
                    })

            # Parse Cough Events
            cough_events = raw_payload.get("cough_events", [])
            for event in cough_events:
                time_str = event.get("timestamp")
                count = event.get("count")
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
                raise ValueError(f"Failed to parse custom Snore & Cough payload: {str(e)}")
            raise e
