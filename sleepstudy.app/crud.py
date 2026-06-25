import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

import database as db_models

def get_sleep_sessions(db: Session, limit: int = 100):
    """Retrieve all sleep sessions ordered by date descending."""
    return db.query(db_models.SleepSession).order_by(db_models.SleepSession.date.desc()).limit(limit).all()

def get_sleep_session(db: Session, session_id: str):
    """Retrieve a single sleep session by ID."""
    return db.query(db_models.SleepSession).filter(db_models.SleepSession.id == session_id).first()

def create_sleep_session(
    db: Session, 
    session_id: str, 
    date: str, 
    start_time: Optional[datetime], 
    end_time: Optional[datetime], 
    sleep_score: int = None,
    resting_heart_rate: int = None,
    avg_overnight_hrv: int = None,
    hrv_status: str = None,
    body_battery_change: int = None,
    overwrite_times: bool = True
):
    """Create a new sleep session or update start/end times if it already exists."""
    db_session = get_sleep_session(db, session_id)
    if db_session:
        if overwrite_times:
            if start_time is not None:
                if db_session.start_time:
                    db_session.start_time = min(db_session.start_time, start_time)
                else:
                    db_session.start_time = start_time
            if end_time is not None:
                if db_session.end_time:
                    db_session.end_time = max(db_session.end_time, end_time)
                else:
                    db_session.end_time = end_time
        if sleep_score is not None:
            db_session.sleep_score = sleep_score
        if resting_heart_rate is not None:
            db_session.resting_heart_rate = resting_heart_rate
        if avg_overnight_hrv is not None:
            db_session.avg_overnight_hrv = avg_overnight_hrv
        if hrv_status is not None:
            db_session.hrv_status = hrv_status
        if body_battery_change is not None:
            db_session.body_battery_change = body_battery_change
    else:
        fallback_start = start_time if start_time is not None else datetime.now()
        fallback_end = end_time if end_time is not None else fallback_start
        db_session = db_models.SleepSession(
            id=session_id,
            date=date,
            start_time=fallback_start,
            end_time=fallback_end,
            sleep_score=sleep_score,
            resting_heart_rate=resting_heart_rate,
            avg_overnight_hrv=avg_overnight_hrv,
            hrv_status=hrv_status,
            body_battery_change=body_battery_change
        )
        db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def update_sleep_session_notes(db: Session, session_id: str, rating: int, notes: str, sleep_position: str = None, sleep_aids: str = None, sleep_disruptors: str = None):
    """Update user ratings, notes, sleep position, sleep aids, and sleep disruptors for a sleep session."""
    db_session = get_sleep_session(db, session_id)
    if db_session:
        db_session.rating = rating
        db_session.notes = notes
        db_session.sleep_position = sleep_position
        db_session.sleep_aids = sleep_aids
        db_session.sleep_disruptors = sleep_disruptors
        db.commit()
        db.refresh(db_session)
    return db_session

def add_metric_samples(db: Session, samples_data: list):
    """
    Bulk insert a list of metric samples.
    samples_data is a list of dicts matching SleepMetricSample columns.
    """
    db_samples = []
    for sample in samples_data:
        db_sample = db_models.SleepMetricSample(
            session_id=sample["session_id"],
            connector_id=sample["connector_id"],
            metric_type=sample["metric_type"],
            timestamp=sample["timestamp"],
            value_numeric=sample.get("value_numeric"),
            value_text=sample.get("value_text"),
            raw_payload=json.dumps(sample.get("raw_payload")) if sample.get("raw_payload") else None
        )
        db_samples.append(db_sample)
    
    db.add_all(db_samples)
    db.commit()
    return len(db_samples)

def delete_sleep_session(db: Session, session_id: str):
    """Delete a sleep session and cascade delete its samples."""
    db_session = get_sleep_session(db, session_id)
    if db_session:
        db.delete(db_session)
        db.commit()
        return True
    return False

def get_session_details_aligned(db: Session, session_id: str):
    """
    Retrieve all session details and metrics, pre-grouped by metric_type and connector_id
    to simplify time-aligned overlays on the dashboard.
    """
    session = get_sleep_session(db, session_id)
    if not session:
        return None
    
    # Query all samples for this session, ordered by timestamp
    samples = db.query(db_models.SleepMetricSample).filter(
        db_models.SleepMetricSample.session_id == session_id
    ).order_by(db_models.SleepMetricSample.timestamp.asc()).all()

    # Structure data for frontend alignment
    # Format: { metric_type: { connector_id: [ { t: ISO_Timestamp, v: numeric_or_text_val }, ... ] } }
    metrics_grouped = {}
    
    for sample in samples:
        m_type = sample.metric_type
        c_id = sample.connector_id
        
        if m_type not in metrics_grouped:
            metrics_grouped[m_type] = {}
        if c_id not in metrics_grouped[m_type]:
            metrics_grouped[m_type][c_id] = []
            
        val = sample.value_numeric if sample.value_numeric is not None else sample.value_text
        metrics_grouped[m_type][c_id].append({
            "t": sample.timestamp.isoformat() + "Z",
            "v": val,
            "raw_payload": json.loads(sample.raw_payload) if sample.raw_payload else None
        })

    # Find which connectors contributed to this session
    connectors_present = list(set(sample.connector_id for sample in samples))

    return {
        "session": session.to_dict(),
        "connectors": connectors_present,
        "metrics": metrics_grouped
    }

def get_connector_config(db: Session, connector_id: str) -> dict:
    """Retrieve all configuration keys and values for a specific connector."""
    configs = db.query(db_models.ConnectorConfig).filter(
        db_models.ConnectorConfig.connector_id == connector_id
    ).all()
    return {c.config_key: c.config_value for c in configs}

def save_connector_config(db: Session, connector_id: str, config_dict: dict):
    """Save or update configuration key-values for a connector."""
    for key, value in config_dict.items():
        db_config = db.query(db_models.ConnectorConfig).filter(
            and_(
                db_models.ConnectorConfig.connector_id == connector_id,
                db_models.ConnectorConfig.config_key == key
            )
        ).first()

        if db_config:
            db_config.config_value = value
        else:
            db_config = db_models.ConnectorConfig(
                connector_id=connector_id,
                config_key=key,
                config_value=value
            )
            db.add(db_config)
            
    db.commit()


def get_sleep_aids(db: Session):
    """Retrieve all configured sleep aids ordered by name."""
    return db.query(db_models.SleepAid).order_by(db_models.SleepAid.name.asc()).all()

def create_sleep_aid(db: Session, name: str, category: str = "aid"):
    """Create a new unique sleep aid or disruptor tag. If it already exists, return it."""
    # Normalise name to strip leading/trailing whitespace
    name = name.strip()
    existing = db.query(db_models.SleepAid).filter(db_models.SleepAid.name == name).first()
    if existing:
        return existing
    
    db_aid = db_models.SleepAid(name=name, category=category)
    db.add(db_aid)
    db.commit()
    db.refresh(db_aid)
    return db_aid

def delete_sleep_aid(db: Session, aid_id: int):
    """Delete a sleep aid configuration by ID."""
    db_aid = db.query(db_models.SleepAid).filter(db_models.SleepAid.id == aid_id).first()
    if db_aid:
        db.delete(db_aid)
        db.commit()
        return True
    return False


