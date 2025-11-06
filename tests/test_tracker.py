"""
Tests for the main tracker functionality.
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta

from deutsch_verfahrn.tracker import LatenessTracker
from deutsch_verfahrn.models import TripClass


class TestLatenessTracker(unittest.TestCase):
    """Tests for LatenessTracker."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.tracker = LatenessTracker(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_add_trip_from_shared_data(self):
        """Test adding trip from shared data."""
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 89.90,
            "train_number": "ICE 123",
            "class": "2nd Class"
        }
        
        trip = self.tracker.add_trip_from_shared_data(data)
        self.assertEqual(trip.origin, "Berlin Hbf")
        self.assertEqual(trip.destination, "München Hbf")
        self.assertEqual(trip.ticket_price, 89.90)
        self.assertEqual(trip.trip_class, TripClass.SECOND)
    
    def test_update_trip_with_delay(self):
        """Test updating trip with delay and compensation."""
        # Add trip
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 100.0,
            "train_number": "ICE 123"
        }
        trip = self.tracker.add_trip_from_shared_data(data)
        
        # Update with 75 minute delay
        actual_arrival = datetime(2024, 1, 15, 15, 15)
        delay = self.tracker.update_trip_actual_times(
            trip.trip_id,
            actual_arrival=actual_arrival
        )
        
        self.assertIsNotNone(delay)
        self.assertEqual(delay.delay_minutes, 75)
        self.assertEqual(delay.compensation_amount, 25.0)
        self.assertEqual(self.tracker.get_balance(), 25.0)
    
    def test_update_trip_no_compensation(self):
        """Test updating trip without compensation threshold."""
        # Add trip
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 100.0,
            "train_number": "ICE 123"
        }
        trip = self.tracker.add_trip_from_shared_data(data)
        
        # Update with only 30 minute delay
        actual_arrival = datetime(2024, 1, 15, 14, 30)
        delay = self.tracker.update_trip_actual_times(
            trip.trip_id,
            actual_arrival=actual_arrival
        )
        
        self.assertIsNone(delay)
        self.assertEqual(self.tracker.get_balance(), 0.0)
    
    def test_balance_accumulation(self):
        """Test balance accumulation from multiple delays."""
        # Add first trip
        data1 = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 100.0,
            "train_number": "ICE 123"
        }
        trip1 = self.tracker.add_trip_from_shared_data(data1)
        self.tracker.update_trip_actual_times(
            trip1.trip_id,
            actual_arrival=datetime(2024, 1, 15, 15, 30)  # 90 min delay
        )
        
        # Add second trip
        data2 = {
            "origin": "Hamburg Hbf",
            "destination": "Frankfurt Hbf",
            "scheduled_departure": "2024-01-20T08:00:00",
            "scheduled_arrival": "2024-01-20T11:00:00",
            "ticket_price": 80.0,
            "train_number": "ICE 456"
        }
        trip2 = self.tracker.add_trip_from_shared_data(data2)
        self.tracker.update_trip_actual_times(
            trip2.trip_id,
            actual_arrival=datetime(2024, 1, 20, 13, 30)  # 150 min delay
        )
        
        # Check balance: 25.0 + 40.0 = 65.0
        self.assertEqual(self.tracker.get_balance(), 65.0)
        self.assertTrue(self.tracker.can_file_claim())
    
    def test_generate_reimbursement_form(self):
        """Test reimbursement form generation."""
        # Add trip with delay
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 100.0,
            "train_number": "ICE 123"
        }
        trip = self.tracker.add_trip_from_shared_data(data)
        self.tracker.update_trip_actual_times(
            trip.trip_id,
            actual_arrival=datetime(2024, 1, 15, 15, 30)
        )
        
        # Generate form
        form = self.tracker.generate_reimbursement_form(
            user_name="Max Mustermann",
            user_address="Hauptstraße 1, 10115 Berlin",
            user_iban="DE89370400440532013000"
        )
        
        self.assertIsNotNone(form)
        self.assertEqual(form.total_amount, 25.0)
        self.assertEqual(form.user_name, "Max Mustermann")
        self.assertEqual(len(form.delays), 1)
        
        # Check balance was reset
        self.assertEqual(self.tracker.get_balance(), 0.0)
    
    def test_cannot_generate_form_insufficient_balance(self):
        """Test form generation fails with insufficient balance."""
        form = self.tracker.generate_reimbursement_form(
            user_name="Max Mustermann",
            user_address="Hauptstraße 1, 10115 Berlin",
            user_iban="DE89370400440532013000"
        )
        
        self.assertIsNone(form)
    
    def test_suggest_alternatives(self):
        """Test alternative route suggestions."""
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 100.0,
            "train_number": "ICE 123"
        }
        trip = self.tracker.add_trip_from_shared_data(data)
        
        # Get alternatives for 60 minute delay
        alternatives = self.tracker.suggest_alternatives(trip, 60)
        
        self.assertIsInstance(alternatives, list)
        # Should suggest alternatives for significant delays
        self.assertGreater(len(alternatives), 0)
    
    def test_persistence(self):
        """Test data persistence across tracker instances."""
        # Add trip and delay
        data = {
            "origin": "Berlin Hbf",
            "destination": "München Hbf",
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T14:00:00",
            "ticket_price": 100.0,
            "train_number": "ICE 123"
        }
        trip = self.tracker.add_trip_from_shared_data(data)
        self.tracker.update_trip_actual_times(
            trip.trip_id,
            actual_arrival=datetime(2024, 1, 15, 15, 30)
        )
        
        initial_balance = self.tracker.get_balance()
        
        # Create new tracker with same database
        tracker2 = LatenessTracker(self.db_path)
        
        # Balance should be persisted
        self.assertEqual(tracker2.get_balance(), initial_balance)


if __name__ == "__main__":
    unittest.main()
