import importlib.util
import sys
import inspect
from pathlib import Path
from sqlalchemy.orm import Session

import config
import crud
from connectors.base import BaseConnector

# Global dictionary of active, loaded connectors
active_connectors = {}

def load_connectors():
    """
    Scans the native app connectors folder and the persistent appdata custom connectors folder.
    Dynamically loads any subclass of BaseConnector.
    """
    global active_connectors
    active_connectors.clear()
    
    # We load native connectors first, then custom connectors (which can override native ones)
    search_dirs = [
        ("native", config.NATIVE_CONNECTORS_DIR),
        ("custom", config.CUSTOM_CONNECTORS_DIR)
    ]
    
    for origin, directory in search_dirs:
        if not directory.exists():
            continue
            
        print(f"Scanning {origin} connectors directory: {directory}")
        for file_path in directory.glob("*.py"):
            # Skip init and base helper files
            if file_path.name in ["__init__.py", "base.py"]:
                continue
                
            try:
                module_name = f"connectors_{origin}_{file_path.stem}"
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if not spec or not spec.loader:
                    continue
                module = importlib.util.module_from_spec(spec)
                
                # Make sure dynamic module resides in sys.modules so internal imports work
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Find classes inheriting from BaseConnector
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BaseConnector) and obj != BaseConnector:
                        connector_instance = obj()
                        cid = connector_instance.connector_id
                        
                        # Register the connector
                        active_connectors[cid] = connector_instance
                        print(f"Successfully loaded {origin} connector: '{cid}' ({connector_instance.display_name})")
                        
            except Exception as e:
                print(f"Error loading connector from '{file_path}': {e}")
                
    return active_connectors

def import_raw_payload(db: Session, connector_id: str, raw_payload: dict):
    """
    Ingest raw JSON payload using the specified connector.
    Parses details, creates/updates the SleepSession, and inserts time-series metric samples.
    """
    print(f"[Import] Ingesting payload for connector '{connector_id}'...")
    connector = active_connectors.get(connector_id)
    if not connector:
        raise ValueError(f"Connector '{connector_id}' is not loaded or does not exist.")
        
    # 1. Parse the payload using the connector
    parsed_data = connector.parse_payload(raw_payload)
    session_info = parsed_data["session"]
    samples_list = parsed_data["samples"]
    
    print(f"[Import] Parsed session for date {session_info['date']} (onset: {session_info['start_time']}, wake: {session_info['end_time']})")
    
    # 2. Upsert Sleep Session
    session = crud.create_sleep_session(
        db=db,
        session_id=session_info["session_id"],
        date=session_info["date"],
        start_time=session_info["start_time"],
        end_time=session_info["end_time"],
        sleep_score=session_info.get("sleep_score"),
        resting_heart_rate=session_info.get("resting_heart_rate"),
        avg_overnight_hrv=session_info.get("avg_overnight_hrv"),
        hrv_status=session_info.get("hrv_status"),
        body_battery_change=session_info.get("body_battery_change")
    )
    
    # 3. Add session_id to samples and bulk insert
    for sample in samples_list:
        sample["session_id"] = session.id
        sample["connector_id"] = connector_id
        
    inserted_count = crud.add_metric_samples(db, samples_list)
    print(f"[Import] Successfully imported {inserted_count} metric samples for session '{session.id}'.")
    
    return {
        "status": "success",
        "connector_id": connector_id,
        "session_id": session.id,
        "date": session.date,
        "samples_imported": inserted_count
    }
