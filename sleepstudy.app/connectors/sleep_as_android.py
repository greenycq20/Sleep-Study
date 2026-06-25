from datetime import datetime, timedelta
from typing import Dict, Any, List
from connectors.base import BaseConnector

class SleepAsAndroidConnector(BaseConnector):
    @property
    def connector_id(self) -> str:
        return "sleep_as_android"

    @property
    def display_name(self) -> str:
        return "Sleep as Android"

    @property
    def description(self) -> str:
        return "Ingests real-time snoring, coughing, and tracking state events pushed automatically via webhooks."

    def parse_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses a single real-time Sleep as Android webhook event.
        Payload format:
        {
          "event": "event_name",
          "value1": "optional_data",
          "value2": "optional_data",
          "value3": "optional_data"
        }
        """
        try:
            event_name = raw_payload.get("event") or raw_payload.get("event_name")
            if not event_name:
                raise ValueError("Payload missing required 'event' or 'event_name' key.")

            # 1. Parse Event Timestamp (extract from value1/timestamp or default to local now)
            timestamp = datetime.now()
            for field in ["timestamp", "value1", "value2"]:
                val = raw_payload.get(field)
                if val:
                    # Check if val is a numeric string representing UNIX timestamp
                    try:
                        ts = float(val)
                        if ts > 1e11:  # Milliseconds
                            timestamp = datetime.fromtimestamp(ts / 1000.0)
                        else:  # Seconds
                            timestamp = datetime.fromtimestamp(ts)
                        break
                    except (ValueError, TypeError):
                        # Try parsing as ISO format if possible
                        try:
                            timestamp = datetime.fromisoformat(val)
                            break
                        except ValueError:
                            pass

            # 2. Determine morning date for sleep session mapping
            # If tracking starts/event occurs noon or later, it belongs to tomorrow morning's date.
            # If it occurs before noon, it belongs to today morning's date.
            if timestamp.hour >= 12:
                morning_date = (timestamp + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                morning_date = timestamp.strftime("%Y-%m-%d")

            session_id = f"garmin_{morning_date.replace('-', '')}"

            # 3. Handle specific event logic
            # Standardize event names
            event_lower = event_name.lower()
            start_time = None
            end_time = None
            overwrite_times = False
            samples = []

            # Mapping of sound events to standard metric types
            sound_metrics = {
                "sound_event_snore": "snore",
                "snore": "snore",
                "snoring": "snore",
                "sound_event_cough": "cough",
                "cough": "cough",
                "coughing": "cough",
                "sound_event_talk": "talk",
                "talk": "talk",
                "talking": "talk",
                "sound_event_baby": "baby",
                "baby": "baby",
                "baby_cry": "baby",
                "sound_event_laugh": "laugh",
                "laugh": "laugh",
                "laughter": "laugh"
            }

            if event_lower == "sleep_tracking_started":
                start_time = timestamp
                end_time = timestamp
                overwrite_times = True
            elif event_lower in ["sleep_tracking_stopped", "sleep_tracking_finished"]:
                end_time = timestamp
                overwrite_times = True
            elif event_lower in sound_metrics:
                metric_type = sound_metrics[event_lower]
                # Occurrence sound event (count 1.0)
                samples.append({
                    "metric_type": metric_type,
                    "timestamp": timestamp,
                    "value_numeric": 1.0,
                    "raw_payload": raw_payload
                })

            session_data = {
                "session_id": session_id,
                "date": morning_date,
                "start_time": start_time,
                "end_time": end_time,
                "overwrite_times": overwrite_times
            }

            return {
                "session": session_data,
                "samples": samples
            }

        except Exception as e:
            if not isinstance(e, ValueError):
                raise ValueError(f"Failed to parse Sleep as Android payload: {str(e)}")
            raise e
