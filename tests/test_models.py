"""
Tests for domain models.
"""

import unittest
from datetime import datetime, timedelta

from deutsch_verfahrn.models import (
    Trip, Delay, VirtualBalance, AlternativeRoute,
    ReimbursementForm, TripClass, DelayType
)


class TestTrip(unittest.TestCase):
    """Tests for Trip model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scheduled_departure = datetime(2024, 1, 15, 10, 0)
        self.scheduled_arrival = datetime(2024, 1, 15, 12, 0)
        self.trip = Trip(
            trip_id="test-123",
            origin="Berlin Hbf",
            destination="München Hbf",
            scheduled_departure=self.scheduled_departure,
            scheduled_arrival=self.scheduled_arrival,
            ticket_price=89.90,
            train_number="ICE 123"
        )
    
    def test_no_delay(self):
        """Test trip with no delay."""
        self.trip.actual_arrival = self.scheduled_arrival
        self.assertEqual(self.trip.get_delay_minutes(), 0)
        self.assertFalse(self.trip.is_delayed())
    
    def test_delay_calculation(self):
        """Test delay calculation."""
        self.trip.actual_arrival = self.scheduled_arrival + timedelta(minutes=75)
        self.assertEqual(self.trip.get_delay_minutes(), 75)
        self.assertTrue(self.trip.is_delayed(threshold_minutes=60))
    
    def test_early_arrival(self):
        """Test early arrival (no negative delay)."""
        self.trip.actual_arrival = self.scheduled_arrival - timedelta(minutes=10)
        self.assertEqual(self.trip.get_delay_minutes(), 0)


class TestDelay(unittest.TestCase):
    """Tests for Delay model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.trip = Trip(
            trip_id="test-123",
            origin="Berlin Hbf",
            destination="München Hbf",
            scheduled_departure=datetime(2024, 1, 15, 10, 0),
            scheduled_arrival=datetime(2024, 1, 15, 12, 0),
            ticket_price=100.0,
            train_number="ICE 123"
        )
    
    def test_compensation_60_minutes(self):
        """Test 25% compensation for 60-119 minute delay."""
        delay = Delay(trip=self.trip, delay_minutes=60)
        compensation = delay.calculate_compensation()
        self.assertEqual(compensation, 25.0)
        self.assertEqual(delay.compensation_percentage, 25.0)
    
    def test_compensation_90_minutes(self):
        """Test 25% compensation for 90 minute delay."""
        delay = Delay(trip=self.trip, delay_minutes=90)
        compensation = delay.calculate_compensation()
        self.assertEqual(compensation, 25.0)
        self.assertEqual(delay.compensation_percentage, 25.0)
    
    def test_compensation_120_minutes(self):
        """Test 50% compensation for 120+ minute delay."""
        delay = Delay(trip=self.trip, delay_minutes=120)
        compensation = delay.calculate_compensation()
        self.assertEqual(compensation, 50.0)
        self.assertEqual(delay.compensation_percentage, 50.0)
    
    def test_no_compensation_under_threshold(self):
        """Test no compensation for delays under 60 minutes."""
        delay = Delay(trip=self.trip, delay_minutes=45)
        compensation = delay.calculate_compensation()
        self.assertEqual(compensation, 0.0)
        self.assertEqual(delay.compensation_percentage, 0.0)


class TestVirtualBalance(unittest.TestCase):
    """Tests for VirtualBalance model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.balance = VirtualBalance(threshold_for_claim=4.0)
        self.trip = Trip(
            trip_id="test-123",
            origin="Berlin Hbf",
            destination="München Hbf",
            scheduled_departure=datetime(2024, 1, 15, 10, 0),
            scheduled_arrival=datetime(2024, 1, 15, 12, 0),
            ticket_price=100.0
        )
    
    def test_add_delay_with_compensation(self):
        """Test adding delay with compensation."""
        delay = Delay(trip=self.trip, delay_minutes=60)
        compensation = self.balance.add_delay(delay)
        self.assertEqual(compensation, 25.0)
        self.assertEqual(self.balance.balance, 25.0)
        self.assertEqual(self.balance.get_total_delays(), 1)
    
    def test_add_delay_without_compensation(self):
        """Test adding delay without compensation."""
        delay = Delay(trip=self.trip, delay_minutes=30)
        compensation = self.balance.add_delay(delay)
        self.assertEqual(compensation, 0.0)
        self.assertEqual(self.balance.balance, 0.0)
    
    def test_can_file_claim(self):
        """Test claim filing threshold."""
        self.assertFalse(self.balance.can_file_claim())
        
        delay = Delay(trip=self.trip, delay_minutes=60)
        self.balance.add_delay(delay)
        self.assertTrue(self.balance.can_file_claim())
    
    def test_reset_balance(self):
        """Test balance reset."""
        delay = Delay(trip=self.trip, delay_minutes=60)
        self.balance.add_delay(delay)
        
        claimed = self.balance.reset_balance()
        self.assertEqual(claimed, 25.0)
        self.assertEqual(self.balance.balance, 0.0)


class TestAlternativeRoute(unittest.TestCase):
    """Tests for AlternativeRoute model."""
    
    def test_is_faster(self):
        """Test faster route detection."""
        original_arrival = datetime(2024, 1, 15, 12, 0)
        earlier_arrival = datetime(2024, 1, 15, 11, 30)
        later_arrival = datetime(2024, 1, 15, 12, 30)
        
        alt1 = AlternativeRoute(
            mode="ICE",
            estimated_arrival=earlier_arrival
        )
        self.assertTrue(alt1.is_faster(original_arrival))
        
        alt2 = AlternativeRoute(
            mode="IC",
            estimated_arrival=later_arrival
        )
        self.assertFalse(alt2.is_faster(original_arrival))


class TestReimbursementForm(unittest.TestCase):
    """Tests for ReimbursementForm model."""
    
    def test_export_to_text(self):
        """Test form export to text."""
        trip = Trip(
            trip_id="test-123",
            origin="Berlin Hbf",
            destination="München Hbf",
            scheduled_departure=datetime(2024, 1, 15, 10, 0),
            scheduled_arrival=datetime(2024, 1, 15, 12, 0),
            actual_arrival=datetime(2024, 1, 15, 13, 30),
            ticket_price=100.0,
            train_number="ICE 123"
        )
        
        delay = Delay(trip=trip, delay_minutes=90)
        delay.calculate_compensation()
        
        form = ReimbursementForm(
            form_id="form-123",
            user_name="Max Mustermann",
            user_address="Hauptstraße 1, 10115 Berlin",
            user_iban="DE89370400440532013000",
            total_amount=25.0,
            delays=[delay]
        )
        
        text = form.export_to_text()
        self.assertIn("Max Mustermann", text)
        self.assertIn("DE89370400440532013000", text)
        self.assertIn("ICE 123", text)
        self.assertIn("€25.00", text)
        self.assertIn("Berlin Hbf → München Hbf", text)


if __name__ == "__main__":
    unittest.main()
