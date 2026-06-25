import uvicorn
import queue
import threading
import time
import traceback
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from pydantic import BaseModel

import config
import database as db_models
from database import init_db, SessionLocal
import crud
import connector_manager

def run_garmin_auto_sync():
    """Background loop that periodically checks and runs auto-sync for the current morning's sleep."""
    print("[Auto Sync] Background worker thread started.")
    # Give the server a few seconds to boot fully before starting sync checks
    time.sleep(10)
    while True:
        try:
            # Create a localized DB session
            db = SessionLocal()
            try:
                configs = crud.get_connector_config(db, "garmin")
                auto_sync = configs.get("auto_sync") == "true"
                email = configs.get("email")
                password = configs.get("password")

                if auto_sync and email and password:
                    # Today's date (local morning date)
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    # Check if session already exists
                    existing = db.query(db_models.SleepSession).filter(db_models.SleepSession.date == today_str).first()
                    if not existing:
                        print(f"[Auto Sync] Sleep record for morning date {today_str} not found in DB. Triggering Garmin sync...")
                        connector = connector_manager.active_connectors.get("garmin")
                        if connector:
                            parsed_data = connector.fetch_data(db, today_str)
                            if parsed_data and parsed_data.get("session"):
                                session_info = parsed_data["session"]
                                samples_list = parsed_data["samples"]
                                
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
                                
                                for sample in samples_list:
                                    sample["session_id"] = session.id
                                    sample["connector_id"] = "garmin"
                                    
                                inserted = crud.add_metric_samples(db, samples_list)
                                print(f"[Auto Sync] SUCCESS: Synced sleep session for {session.date} with {inserted} metrics.")
                            else:
                                print(f"[Auto Sync] Garmin sync run checked for {today_str}, but no sleep record was found on Garmin Connect (yet).")
                        else:
                            print("[Auto Sync] Garmin connector not active.")
            finally:
                db.close()
        except Exception as err:
            print(f"[Auto Sync] Error in background task: {err}")
            traceback.print_exc()
            
        # Check every 1 hour (3600 seconds)
        time.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("Initializing database...")
    init_db()
    print("Loading data connectors...")
    connector_manager.load_connectors()
    
    # Start Garmin Auto Sync Background Thread
    threading.Thread(target=run_garmin_auto_sync, daemon=True).start()
    
    yield
    # Shutdown actions
    pass

app = FastAPI(
    title="sleepstudy.app",
    description="Self-hosted dashboard to review, align, and note sleep datasets.",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic schemas for request validation
class NotesUpdate(BaseModel):
    rating: int
    notes: str
    sleep_position: Optional[str] = None
    sleep_aids: Optional[str] = None

class SleepAidCreate(BaseModel):
    name: str

class SyncRequest(BaseModel):
    date: str  # YYYY-MM-DD


# REST API Endpoints

@app.get("/api/connectors")
def get_connectors():
    """Return all currently loaded connectors (both native and dynamic custom ones)."""
    return [
        {
            "connector_id": conn.connector_id,
            "display_name": conn.display_name,
            "description": conn.description
        }
        for conn in connector_manager.active_connectors.values()
    ]


@app.get("/api/connectors/{connector_id}/config")
def get_connector_config(connector_id: str, db: Session = Depends(get_db)):
    """Retrieve saved configs for a connector, masking passwords for security."""
    configs = crud.get_connector_config(db, connector_id)
    if "password" in configs:
        configs["password"] = "••••••••••••"
    return configs


@app.post("/api/connectors/{connector_id}/config")
def save_connector_config(connector_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Save or update configs for a connector, handling password masks."""
    if connector_id == "garmin":
        email = payload.get("email")
        password = payload.get("password")
        auto_sync = payload.get("auto_sync", "false")
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required.")
        
        # If password is masked, reload the existing configuration to preserve the original password
        if password == "••••••••••••":
            existing = crud.get_connector_config(db, connector_id)
            password = existing.get("password")
            if not password:
                raise HTTPException(status_code=400, detail="Existing password not found. Please input password.")
        
        crud.save_connector_config(db, connector_id, {"email": email, "password": password, "auto_sync": auto_sync})
    else:
        crud.save_connector_config(db, connector_id, payload)
    return {"status": "success", "detail": f"Configuration saved for connector '{connector_id}'."}


@app.post("/api/connectors/{connector_id}/import")
def import_connector_data(connector_id: str, payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """
    Ingest a raw payload using the designated connector.
    Saves a SleepSession and its corresponding time-series metrics.
    """
    if connector_id not in connector_manager.active_connectors:
        raise HTTPException(
            status_code=404, 
            detail=f"Connector '{connector_id}' is not loaded. Ensure the connector plugin exists."
        )
    try:
        result = connector_manager.import_raw_payload(db, connector_id, payload)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal import error: {str(e)}")


@app.post("/api/connectors/garmin/sync")
def trigger_garmin_sync(req: SyncRequest, db: Session = Depends(get_db)):
    """
    Actively fetch sleep data for the requested date from Garmin Connect API.
    Streams progress logs to the frontend via StreamingResponse.
    """
    connector = connector_manager.active_connectors.get("garmin")
    if not connector:
        raise HTTPException(status_code=404, detail="Garmin connector is not active.")

    def event_generator():
        log_queue = queue.Queue()

        def log_cb(msg: str):
            log_queue.put(msg)

        def worker():
            try:
                log_cb(f"[INFO] Initializing sync process for target date: {req.date}...\n")
                
                # Fetch data inside background thread. Creates separate db connection inside worker
                worker_db = SessionLocal()
                try:
                    parsed_data = connector.fetch_data(worker_db, req.date, log_callback=log_cb)
                    
                    if parsed_data and parsed_data.get("session"):
                        log_cb("[INFO] Saving fetched data to database...\n")
                        session_info = parsed_data["session"]
                        samples_list = parsed_data["samples"]
                        
                        session = crud.create_sleep_session(
                            db=worker_db,
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
                        
                        # Add session_id and source name to samples
                        for sample in samples_list:
                            sample["session_id"] = session.id
                            sample["connector_id"] = "garmin"
                            
                        inserted = crud.add_metric_samples(worker_db, samples_list)
                        log_cb(f"[SUCCESS] Ingested sleep session for {session.date} with {inserted} metrics.\n")
                    else:
                        log_cb("[WARNING] No Garmin sleep record was found or parsed for this date.\n")
                finally:
                    worker_db.close()
                    
            except Exception as e:
                log_cb(f"[ERROR] Sync worker failed: {e}\n")
            finally:
                log_queue.put(None)  # Signal end of stream

        # Launch the Garmin fetching logic in a worker thread to keep it non-blocking
        threading.Thread(target=worker).start()

        # Stream lines from the queue to the client
        while True:
            msg = log_queue.get()
            if msg is None:
                break
            yield msg

    return StreamingResponse(event_generator(), media_type="text/plain")


@app.get("/api/connectors/garmin/raw")
def list_raw_garmin_files():
    """List all saved raw Garmin JSON files."""
    import os
    import glob
    try:
        files = glob.glob(os.path.join(config.DATA_DIR, "garmin_raw_*.json"))
        dates = []
        for f in files:
            base = os.path.basename(f)
            # Extract date from garmin_raw_YYYY-MM-DD.json
            date_part = base[11:-5]
            dates.append(date_part)
        return sorted(dates, reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list raw files: {e}")


@app.get("/api/connectors/garmin/raw/{date_str}")
def get_raw_garmin_file(date_str: str):
    """Retrieve the content of a raw Garmin JSON file."""
    import os
    import json
    file_name = f"garmin_raw_{date_str}.json"
    file_path = os.path.join(config.DATA_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Raw Garmin file not found: {file_name}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")


@app.get("/api/sessions")
def get_sessions(db: Session = Depends(get_db)):
    """Retrieve all historical sleep sessions."""
    sessions = crud.get_sleep_sessions(db)
    return [s.to_dict() for s in sessions]


@app.get("/api/sessions/{session_id}")
def get_session_details(session_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed metadata and pre-grouped, time-aligned metric series for a sleep session."""
    aligned_data = crud.get_session_details_aligned(db, session_id)
    if not aligned_data:
        raise HTTPException(status_code=404, detail="Sleep session not found.")
    return aligned_data


@app.post("/api/sessions/{session_id}/notes")
def update_session_notes(session_id: str, notes_data: NotesUpdate, db: Session = Depends(get_db)):
    """Update user ratings, notes, sleep position, and sleep aids for a specific sleep session."""
    session = crud.update_sleep_session_notes(
        db=db,
        session_id=session_id,
        rating=notes_data.rating,
        notes=notes_data.notes,
        sleep_position=notes_data.sleep_position,
        sleep_aids=notes_data.sleep_aids
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sleep session not found.")
    return session.to_dict()


@app.get("/api/sleep_aids")
def get_sleep_aids(db: Session = Depends(get_db)):
    """Retrieve all configured sleep aid tags."""
    aids = crud.get_sleep_aids(db)
    return [a.to_dict() for a in aids]


@app.post("/api/sleep_aids")
def create_sleep_aid(aid_data: SleepAidCreate, db: Session = Depends(get_db)):
    """Create a new unique sleep aid tag."""
    if not aid_data.name.strip():
        raise HTTPException(status_code=400, detail="Sleep aid name cannot be empty.")
    aid = crud.create_sleep_aid(db, aid_data.name)
    return aid.to_dict()


@app.delete("/api/sleep_aids/{aid_id}")
def delete_sleep_aid(aid_id: int, db: Session = Depends(get_db)):
    """Delete a sleep aid configuration tag by ID."""
    success = crud.delete_sleep_aid(db, aid_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sleep aid tag not found.")
    return {"status": "success", "detail": f"Sleep aid tag {aid_id} deleted."}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a sleep session and all associated metrics."""
    success = crud.delete_sleep_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sleep session not found.")
    return {"status": "success", "detail": f"Session {session_id} and all related metrics deleted."}


# Mount the frontend static files at root
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import os
    print(f"Starting server on port {config.PORT}...")
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=False)
