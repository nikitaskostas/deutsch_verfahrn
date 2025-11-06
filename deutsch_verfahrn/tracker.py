"""
Main lateness tracker implementation.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from .models import (
    Trip, Delay, VirtualBalance, AlternativeRoute, 
    ReimbursementForm, DelayType
)
from .parser import TripParser
from .alternatives import AlternativeTransportSuggester


class LatenessTracker:
    """
    Main tracker for managing trip delays, virtual balance, and reimbursements.
    """
    
    def __init__(self, db_path: str = "lateness_tracker.db"):
        """Initialize the tracker with a database."""
        self.db_path = db_path
        self.virtual_balance = VirtualBalance()
        self.parser = TripParser()
        self.suggester = AlternativeTransportSuggester()
        self._init_database()
        self._load_balance()
    
    def _init_database(self):
        """Initialize SQLite database for persistence."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create trips table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                trip_id TEXT PRIMARY KEY,
                origin TEXT,
                destination TEXT,
                scheduled_departure TEXT,
                scheduled_arrival TEXT,
                actual_departure TEXT,
                actual_arrival TEXT,
                ticket_price REAL,
                trip_class TEXT,
                train_number TEXT
            )
        """)
        
        # Create delays table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id TEXT,
                delay_minutes INTEGER,
                delay_type TEXT,
                compensation_percentage REAL,
                compensation_amount REAL,
                timestamp TEXT,
                claimed INTEGER DEFAULT 0,
                FOREIGN KEY (trip_id) REFERENCES trips (trip_id)
            )
        """)
        
        # Create balance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS balance (
                id INTEGER PRIMARY KEY,
                balance REAL,
                threshold_for_claim REAL
            )
        """)
        
        # Create reimbursement forms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reimbursement_forms (
                form_id TEXT PRIMARY KEY,
                user_name TEXT,
                user_address TEXT,
                user_iban TEXT,
                total_amount REAL,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_balance(self):
        """Load virtual balance from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT balance, threshold_for_claim FROM balance WHERE id = 1")
        row = cursor.fetchone()
        
        if row:
            self.virtual_balance.balance = row[0]
            self.virtual_balance.threshold_for_claim = row[1]
            # Load unclaimed delays
            self.virtual_balance.delays = self._get_unclaimed_delays()
        else:
            # Initialize balance in database
            cursor.execute(
                "INSERT INTO balance (id, balance, threshold_for_claim) VALUES (1, 0.0, 4.0)"
            )
            conn.commit()
        
        conn.close()
    
    def _save_balance(self):
        """Save virtual balance to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE balance SET balance = ?, threshold_for_claim = ? WHERE id = 1",
            (self.virtual_balance.balance, self.virtual_balance.threshold_for_claim)
        )
        
        conn.commit()
        conn.close()
    
    def add_trip_from_shared_data(self, shared_data: Dict[str, Any]) -> Trip:
        """
        Parse shared trip data from DB smartphone app and add to tracker.
        
        Args:
            shared_data: Dictionary containing trip information
            
        Returns:
            Trip object
        """
        trip = self.parser.parse_trip(shared_data)
        self._save_trip(trip)
        return trip
    
    def _save_trip(self, trip: Trip):
        """Save trip to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trips VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trip.trip_id,
            trip.origin,
            trip.destination,
            trip.scheduled_departure.isoformat(),
            trip.scheduled_arrival.isoformat(),
            trip.actual_departure.isoformat() if trip.actual_departure else None,
            trip.actual_arrival.isoformat() if trip.actual_arrival else None,
            trip.ticket_price,
            trip.trip_class.value,
            trip.train_number
        ))
        
        conn.commit()
        conn.close()
    
    def update_trip_actual_times(
        self, 
        trip_id: str, 
        actual_departure: Optional[datetime] = None,
        actual_arrival: Optional[datetime] = None
    ) -> Optional[Delay]:
        """
        Update trip with actual times and check for delays.
        
        Args:
            trip_id: Trip identifier
            actual_departure: Actual departure time
            actual_arrival: Actual arrival time
            
        Returns:
            Delay object if compensation is applicable, None otherwise
        """
        trip = self._load_trip(trip_id)
        if not trip:
            return None
        
        if actual_departure:
            trip.actual_departure = actual_departure
        if actual_arrival:
            trip.actual_arrival = actual_arrival
        
        self._save_trip(trip)
        
        # Check for delays and calculate compensation
        delay_minutes = trip.get_delay_minutes()
        if delay_minutes >= 60:  # DB compensation threshold
            delay = Delay(
                trip=trip,
                delay_minutes=delay_minutes,
                delay_type=DelayType.ARRIVAL_DELAY
            )
            compensation = self.virtual_balance.add_delay(delay)
            self._save_delay(delay)
            self._save_balance()
            
            return delay
        
        return None
    
    def _load_trip(self, trip_id: str) -> Optional[Trip]:
        """Load trip from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            from .models import TripClass
            return Trip(
                trip_id=row[0],
                origin=row[1],
                destination=row[2],
                scheduled_departure=datetime.fromisoformat(row[3]),
                scheduled_arrival=datetime.fromisoformat(row[4]),
                actual_departure=datetime.fromisoformat(row[5]) if row[5] else None,
                actual_arrival=datetime.fromisoformat(row[6]) if row[6] else None,
                ticket_price=row[7],
                trip_class=TripClass.FIRST if row[8] == "1st Class" else TripClass.SECOND,
                train_number=row[9]
            )
        return None
    
    def _save_delay(self, delay: Delay):
        """Save delay to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO delays (trip_id, delay_minutes, delay_type, 
                               compensation_percentage, compensation_amount, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            delay.trip.trip_id,
            delay.delay_minutes,
            delay.delay_type.value,
            delay.compensation_percentage,
            delay.compensation_amount,
            delay.timestamp.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_balance(self) -> float:
        """Get current virtual balance."""
        return self.virtual_balance.balance
    
    def can_file_claim(self) -> bool:
        """Check if balance is sufficient to file a reimbursement claim."""
        return self.virtual_balance.can_file_claim()
    
    def suggest_alternatives(
        self, 
        trip: Trip, 
        current_delay_minutes: int
    ) -> List[AlternativeRoute]:
        """
        Suggest alternative transportation when significant delay occurs.
        
        Args:
            trip: Current trip
            current_delay_minutes: Current delay in minutes
            
        Returns:
            List of alternative routes
        """
        return self.suggester.get_alternatives(trip, current_delay_minutes)
    
    def generate_reimbursement_form(
        self,
        user_name: str,
        user_address: str,
        user_iban: str
    ) -> Optional[ReimbursementForm]:
        """
        Generate reimbursement form for filing with Deutsche Bahn.
        
        Args:
            user_name: User's full name
            user_address: User's address
            user_iban: User's IBAN for reimbursement
            
        Returns:
            ReimbursementForm object if balance is sufficient, None otherwise
        """
        if not self.can_file_claim():
            return None
        
        form = ReimbursementForm(
            form_id=str(uuid4()),
            user_name=user_name,
            user_address=user_address,
            user_iban=user_iban,
            total_amount=self.virtual_balance.balance,
            delays=self.virtual_balance.delays.copy()
        )
        
        self._save_reimbursement_form(form)
        
        # Mark all delays as claimed
        self._mark_delays_as_claimed()
        
        # Reset balance after generating form
        self.virtual_balance.reset_balance()
        self.virtual_balance.delays.clear()
        self._save_balance()
        
        return form
    
    def _save_reimbursement_form(self, form: ReimbursementForm):
        """Save reimbursement form to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reimbursement_forms VALUES (?, ?, ?, ?, ?, ?)
        """, (
            form.form_id,
            form.user_name,
            form.user_address,
            form.user_iban,
            form.total_amount,
            form.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _mark_delays_as_claimed(self):
        """Mark all unclaimed delays as claimed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE delays SET claimed = 1 WHERE claimed = 0")
        
        conn.commit()
        conn.close()
    
    def export_form(self, form: ReimbursementForm, output_path: str):
        """Export reimbursement form to file."""
        Path(output_path).write_text(form.export_to_text())
    
    def _get_unclaimed_delays(self) -> List[Delay]:
        """Get unclaimed delays from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d.*, t.* FROM delays d
            JOIN trips t ON d.trip_id = t.trip_id
            WHERE d.claimed = 0
            ORDER BY d.timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        delays = []
        for row in rows:
            from .models import TripClass
            trip = Trip(
                trip_id=row[8],
                origin=row[9],
                destination=row[10],
                scheduled_departure=datetime.fromisoformat(row[11]),
                scheduled_arrival=datetime.fromisoformat(row[12]),
                actual_departure=datetime.fromisoformat(row[13]) if row[13] else None,
                actual_arrival=datetime.fromisoformat(row[14]) if row[14] else None,
                ticket_price=row[15],
                trip_class=TripClass.FIRST if row[16] == "1st Class" else TripClass.SECOND,
                train_number=row[17]
            )
            
            delay = Delay(
                trip=trip,
                delay_minutes=row[2],
                delay_type=DelayType(row[3]),
                compensation_percentage=row[4],
                compensation_amount=row[5],
                timestamp=datetime.fromisoformat(row[6])
            )
            delays.append(delay)
        
        return delays
    
    def get_all_delays(self) -> List[Delay]:
        """Get all delays from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d.*, t.* FROM delays d
            JOIN trips t ON d.trip_id = t.trip_id
            ORDER BY d.timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        delays = []
        for row in rows:
            from .models import TripClass
            trip = Trip(
                trip_id=row[8],
                origin=row[9],
                destination=row[10],
                scheduled_departure=datetime.fromisoformat(row[11]),
                scheduled_arrival=datetime.fromisoformat(row[12]),
                actual_departure=datetime.fromisoformat(row[13]) if row[13] else None,
                actual_arrival=datetime.fromisoformat(row[14]) if row[14] else None,
                ticket_price=row[15],
                trip_class=TripClass.FIRST if row[16] == "1st Class" else TripClass.SECOND,
                train_number=row[17]
            )
            
            delay = Delay(
                trip=trip,
                delay_minutes=row[2],
                delay_type=DelayType(row[3]),
                compensation_percentage=row[4],
                compensation_amount=row[5],
                timestamp=datetime.fromisoformat(row[6])
            )
            delays.append(delay)
        
        return delays
