from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

class BaseConnector(ABC):
    """
    Abstract Base Class that all sleep data connectors must implement.
    Allows modular extension of the Sleep Study Dashboard for various data sources.
    """

    @property
    @abstractmethod
    def connector_id(self) -> str:
        """Unique string identifier for the connector (e.g. 'garmin', 'health_connect')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name for the connector."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of the data source and capability."""
        pass

    @abstractmethod
    def parse_payload(self, raw_payload: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Parses a raw incoming JSON payload and converts it into standard structures
        suitable for database insertion.

        Args:
            raw_payload (dict): The raw JSON dictionary received by the API or imported.

        Returns:
            dict: A dictionary containing:
                - 'session': Dict with keys:
                    - 'session_id' (str, unique session identifier)
                    - 'date' (str, YYYY-MM-DD morning date)
                    - 'start_time' (str or datetime, start of sleep)
                    - 'end_time' (str or datetime, end of sleep)
                    - 'sleep_score' (int, optional sleep quality score)
                - 'samples': List of dicts, each with keys:
                    - 'metric_type' (str: 'sleep_stage', 'heart_rate', 'respiration', 'snore', 'cough')
                    - 'timestamp' (str or datetime)
                    - 'value_numeric' (float, optional)
                    - 'value_text' (str, optional)
                    - 'raw_payload' (dict, optional raw record context)

        Raises:
            ValueError: If the payload is malformed or invalid.
        """
        pass
