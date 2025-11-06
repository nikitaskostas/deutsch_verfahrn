"""
Tests for trip parser.
"""

import unittest
from datetime import datetime

from deutsch_verfahrn.parser import TripParser
from deutsch_verfahrn.models import TripClass


class TestTripParser(unittest.TestCase):
    """Tests for TripParser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = TripParser()
    
    def test_parse_basic_trip(self):
        """Test parsing basic trip data."""
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 89.90,
            "train_number": "ICE 123",
            "class": "2nd Class"
        }
        
        trip = self.parser.parse_trip(data)
        
        self.assertEqual(trip.origin, "Berlin Hbf")
        self.assertEqual(trip.destination, "München Hbf")
        self.assertEqual(trip.ticket_price, 89.90)
        self.assertEqual(trip.train_number, "ICE 123")
        self.assertEqual(trip.trip_class, TripClass.SECOND)
    
    def test_parse_alternative_keys(self):
        """Test parsing with alternative key names."""
        data = {
            "from": "Hamburg Hbf",
            "to": "Frankfurt Hbf",
            "departure": "2024-01-15T08:00:00",
            "arrival": "2024-01-15T11:00:00",
            "price": 75.50,
            "train": "ICE 456"
        }
        
        trip = self.parser.parse_trip(data)
        
        self.assertEqual(trip.origin, "Hamburg Hbf")
        self.assertEqual(trip.destination, "Frankfurt Hbf")
        self.assertEqual(trip.ticket_price, 75.50)
        self.assertEqual(trip.train_number, "ICE 456")
    
    def test_parse_first_class(self):
        """Test parsing first class trip."""
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 150.00,
            "class": "1st Class"
        }
        
        trip = self.parser.parse_trip(data)
        self.assertEqual(trip.trip_class, TripClass.FIRST)
    
    def test_parse_with_actual_times(self):
        """Test parsing trip with actual times."""
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "actual_departure": "2024-01-15T10:05:00",
            "actual_arrival": "2024-01-15T15:30:00",
            "ticket_price": 89.90
        }
        
        trip = self.parser.parse_trip(data)
        
        self.assertIsNotNone(trip.actual_departure)
        self.assertIsNotNone(trip.actual_arrival)
        self.assertEqual(trip.get_delay_minutes(), 90)
    
    def test_parse_various_datetime_formats(self):
        """Test parsing different datetime formats."""
        formats = [
            "2024-01-15T10:00:00",
            "2024-01-15 10:00:00",
            "15.01.2024 10:00",
            "15/01/2024 10:00",
        ]
        
        for fmt in formats:
            data = {
                "origin": "Berlin Hbf",
                "destination": "München Hbf",
                "scheduled_departure": fmt,
                "scheduled_arrival": fmt,
                "ticket_price": 89.90
            }
            
            trip = self.parser.parse_trip(data)
            self.assertIsInstance(trip.scheduled_departure, datetime)
            self.assertIsInstance(trip.scheduled_arrival, datetime)
    
    def test_parse_with_missing_optional_fields(self):
        """Test parsing with missing optional fields."""
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00"
        }
        
        trip = self.parser.parse_trip(data)
        
        self.assertEqual(trip.ticket_price, 0.0)
        self.assertEqual(trip.train_number, "")
        self.assertEqual(trip.trip_class, TripClass.SECOND)


if __name__ == "__main__":
    unittest.main()
