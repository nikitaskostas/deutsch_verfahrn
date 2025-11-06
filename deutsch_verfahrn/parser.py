"""
Parser for Deutsche Bahn trip data from smartphone app.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from .models import Trip, TripClass


class TripParser:
    """Parser for trip data shared from DB smartphone app."""
    
    def parse_trip(self, data: Dict[str, Any]) -> Trip:
        """
        Parse trip data from various formats.
        
        Supports different input formats:
        - DB Navigator app share format
        - Manual input format
        - JSON format
        
        Args:
            data: Dictionary containing trip information
            
        Returns:
            Trip object
        """
        # Generate trip ID if not provided
        trip_id = data.get("trip_id", str(uuid4()))
        
        # Parse origin and destination
        origin = data.get("origin", data.get("from", "Unknown"))
        destination = data.get("destination", data.get("to", "Unknown"))
        
        # Parse times
        scheduled_departure = self._parse_datetime(
            data.get("scheduled_departure", data.get("departure"))
        )
        scheduled_arrival = self._parse_datetime(
            data.get("scheduled_arrival", data.get("arrival"))
        )
        
        # Parse actual times if provided
        actual_departure = None
        if "actual_departure" in data:
            actual_departure = self._parse_datetime(data["actual_departure"])
        
        actual_arrival = None
        if "actual_arrival" in data:
            actual_arrival = self._parse_datetime(data["actual_arrival"])
        
        # Parse ticket price
        ticket_price = float(data.get("ticket_price", data.get("price", 0.0)))
        
        # Parse trip class
        trip_class_str = data.get("class", data.get("trip_class", "2nd Class"))
        if "1" in trip_class_str or "first" in trip_class_str.lower():
            trip_class = TripClass.FIRST
        else:
            trip_class = TripClass.SECOND
        
        # Parse train number
        train_number = data.get("train_number", data.get("train", ""))
        
        return Trip(
            trip_id=trip_id,
            origin=origin,
            destination=destination,
            scheduled_departure=scheduled_departure,
            scheduled_arrival=scheduled_arrival,
            actual_departure=actual_departure,
            actual_arrival=actual_arrival,
            ticket_price=ticket_price,
            trip_class=trip_class,
            train_number=train_number
        )
    
    def _parse_datetime(self, value: Any) -> datetime:
        """
        Parse datetime from various formats.
        
        Supports:
        - ISO format strings (2024-01-15T14:30:00)
        - datetime objects
        - Unix timestamps
        
        Args:
            value: Value to parse as datetime
            
        Returns:
            datetime object
        """
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # Try ISO format first
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
            
            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%d.%m.%Y %H:%M",
                "%d/%m/%Y %H:%M",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        
        if isinstance(value, (int, float)):
            # Assume Unix timestamp
            return datetime.fromtimestamp(value)
        
        # Default to now if parsing fails
        return datetime.now()
