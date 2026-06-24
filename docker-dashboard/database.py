from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json

from config import DATABASE_URL

# Create engine and session factories
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Required for SQLite in multi-threaded environment (FastAPI)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SleepSession(Base):
    """
    Represents a single sleep period (e.g. overnight sleep).
    Acts as the parent entity for all metric samples collected during this window.
    """
    __tablename__ = "sleep_sessions"

    id = Column(String, primary_key=True)  # Unique ID (e.g., UUID or date-based)
    date = Column(String, nullable=False, index=True)  # Target morning date (YYYY-MM-DD)
    start_time = Column(DateTime, nullable=False)  # Sleep onset timestamp
    end_time = Column(DateTime, nullable=False)  # Wake timestamp
    rating = Column(Integer, nullable=True)  # User rating: 1 to 5 stars
    notes = Column(String, nullable=True)  # User's sleep journal/comments
    sleep_score = Column(Integer, nullable=True)  # Overall sleep quality score (0-100)
    resting_heart_rate = Column(Integer, nullable=True)
    avg_overnight_hrv = Column(Integer, nullable=True)
    hrv_status = Column(String, nullable=True)
    body_battery_change = Column(Integer, nullable=True)
    sleep_position = Column(String, nullable=True)
    sleep_aids = Column(String, nullable=True)

    # Relationships
    metrics = relationship("SleepMetricSample", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "start_time": (self.start_time.isoformat() + "Z") if self.start_time else None,
            "end_time": (self.end_time.isoformat() + "Z") if self.end_time else None,
            "rating": self.rating,
            "notes": self.notes,
            "sleep_score": self.sleep_score,
            "resting_heart_rate": self.resting_heart_rate,
            "avg_overnight_hrv": self.avg_overnight_hrv,
            "hrv_status": self.hrv_status,
            "body_battery_change": self.body_battery_change,
            "sleep_position": self.sleep_position,
            "sleep_aids": self.sleep_aids,
        }


class SleepMetricSample(Base):
    """
    Generic table storing time-series data points from all connectors.
    Can capture sleep stages, heart rate, respiration, snore count, etc.
    """
    __tablename__ = "sleep_metric_samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sleep_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    connector_id = Column(String, nullable=False, index=True)  # Source: e.g., 'garmin', 'health_connect', 'sleep_as_android'
    metric_type = Column(String, nullable=False, index=True)  # Type: 'sleep_stage', 'heart_rate', 'respiration', 'snore', 'cough'
    timestamp = Column(DateTime, nullable=False, index=True)  # UTC timestamp of measurement
    
    value_numeric = Column(Float, nullable=True)  # Value for continuous data (e.g. 72.0 bpm, 15.0 breaths/min, count)
    value_text = Column(String, nullable=True)  # Value for categorical data (e.g. 'light', 'deep', 'rem', 'awake')
    raw_payload = Column(String, nullable=True)  # JSON text blob of raw data point from source for debugging/metadata

    # Relationships
    session = relationship("SleepSession", back_populates="metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "connector_id": self.connector_id,
            "metric_type": self.metric_type,
            "timestamp": (self.timestamp.isoformat() + "Z") if self.timestamp else None,
            "value_numeric": self.value_numeric,
            "value_text": self.value_text,
            "raw_payload": json.loads(self.raw_payload) if self.raw_payload else None
        }


class ConnectorConfig(Base):
    """
    Stores key-value configuration parameters for data connectors (e.g., credentials).
    """
    __tablename__ = "connector_configs"

    connector_id = Column(String, primary_key=True, index=True)
    config_key = Column(String, primary_key=True, index=True)
    config_value = Column(String, nullable=False)

    def to_dict(self):
        return {
            "connector_id": self.connector_id,
            "config_key": self.config_key,
            "config_value": self.config_value
        }


class SleepAid(Base):
    """
    Stores custom sleep aid tags defined by the user (e.g., Nose Strips, Eye Mask).
    """
    __tablename__ = "sleep_aids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }


def init_db():
    """Initializes the database tables and performs self-healing schema updates."""
    # 1. Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Check for missing columns in sleep_sessions (self-healing migration)
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("sleep_sessions")]
    
    new_cols = {
        "resting_heart_rate": "INTEGER",
        "avg_overnight_hrv": "INTEGER",
        "hrv_status": "VARCHAR",
        "body_battery_change": "INTEGER",
        "sleep_position": "VARCHAR",
        "sleep_aids": "VARCHAR"
    }
    
    with engine.begin() as conn:
        for col_name, col_type in new_cols.items():
            if col_name not in columns:
                print(f"Migration: Adding missing column '{col_name}' to table 'sleep_sessions'...")
                conn.execute(text(f"ALTER TABLE sleep_sessions ADD COLUMN {col_name} {col_type}"))
