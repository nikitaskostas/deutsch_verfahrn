"""
Domain models for the transportation lateness tracker.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum


class TripClass(Enum):
    """Train class categories."""
    FIRST = "1st Class"
    SECOND = "2nd Class"


class DelayType(Enum):
    """Types of delays for compensation calculation."""
    ARRIVAL_DELAY = "arrival_delay"
    CANCELLATION = "cancellation"
    MISSED_CONNECTION = "missed_connection"


@dataclass
class Trip:
    """Represents a single train trip."""
    trip_id: str
    origin: str
    destination: str
    scheduled_departure: datetime
    scheduled_arrival: datetime
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    ticket_price: float = 0.0
    trip_class: TripClass = TripClass.SECOND
    train_number: str = ""
    
    def get_delay_minutes(self) -> int:
        """Calculate delay in minutes based on actual vs scheduled arrival."""
        if self.actual_arrival and self.scheduled_arrival:
            delay = self.actual_arrival - self.scheduled_arrival
            return max(0, int(delay.total_seconds() / 60))
        return 0
    
    def is_delayed(self, threshold_minutes: int = 60) -> bool:
        """Check if trip delay exceeds the threshold."""
        return self.get_delay_minutes() >= threshold_minutes


@dataclass
class Delay:
    """Represents a delay event with compensation details."""
    trip: Trip
    delay_minutes: int
    delay_type: DelayType = DelayType.ARRIVAL_DELAY
    compensation_percentage: float = 0.0
    compensation_amount: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def calculate_compensation(self) -> float:
        """
        Calculate compensation based on DB Fahrgastrechte rules.
        
        German railway passenger rights compensation:
        - 60-119 minutes delay: 25% of ticket price
        - 120+ minutes delay: 50% of ticket price
        """
        delay_minutes = self.delay_minutes
        ticket_price = self.trip.ticket_price
        
        if delay_minutes >= 120:
            self.compensation_percentage = 50.0
            self.compensation_amount = ticket_price * 0.5
        elif delay_minutes >= 60:
            self.compensation_percentage = 25.0
            self.compensation_amount = ticket_price * 0.25
        else:
            self.compensation_percentage = 0.0
            self.compensation_amount = 0.0
        
        return self.compensation_amount


@dataclass
class VirtualBalance:
    """Manages virtual balance from accumulated compensation."""
    balance: float = 0.0
    delays: List[Delay] = field(default_factory=list)
    threshold_for_claim: float = 4.0  # Minimum 4 EUR to file a claim
    
    def add_delay(self, delay: Delay) -> float:
        """Add a delay to the balance and return the compensation amount."""
        compensation = delay.calculate_compensation()
        if compensation > 0:
            self.balance += compensation
            self.delays.append(delay)
        return compensation
    
    def can_file_claim(self) -> bool:
        """Check if balance is sufficient to file a reimbursement claim."""
        return self.balance >= self.threshold_for_claim
    
    def get_total_delays(self) -> int:
        """Get total number of compensable delays."""
        return len(self.delays)
    
    def reset_balance(self) -> float:
        """Reset balance after filing a claim and return the claimed amount."""
        claimed = self.balance
        self.balance = 0.0
        return claimed


@dataclass
class AlternativeRoute:
    """Represents an alternative transportation option."""
    mode: str  # e.g., "ICE", "IC", "Regional", "Bus", "Taxi"
    estimated_arrival: datetime
    additional_cost: float = 0.0
    description: str = ""
    
    def is_faster(self, original_arrival: datetime) -> bool:
        """Check if this alternative arrives earlier than the original."""
        return self.estimated_arrival < original_arrival


@dataclass
class ReimbursementForm:
    """Represents a reimbursement claim form."""
    form_id: str
    user_name: str
    user_address: str
    user_iban: str
    total_amount: float
    delays: List[Delay]
    created_at: datetime = field(default_factory=datetime.now)
    
    def mask_iban(self) -> str:
        """Return masked IBAN for display (shows last 4 digits only)."""
        if len(self.user_iban) > 4:
            return "****" + self.user_iban[-4:]
        return "****"
    
    def export_to_text(self, mask_sensitive: bool = False) -> str:
        """
        Export form as formatted text for DB Fahrgastrechte.
        
        Args:
            mask_sensitive: If True, masks IBAN in output (for display only)
        """
        iban_display = self.mask_iban() if mask_sensitive else self.user_iban
        
        lines = [
            "=" * 60,
            "DEUTSCHE BAHN FAHRGASTRECHTE - REIMBURSEMENT FORM",
            "=" * 60,
            "",
            f"Form ID: {self.form_id}",
            f"Date: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            "CUSTOMER INFORMATION",
            "-" * 60,
            f"Name: {self.user_name}",
            f"Address: {self.user_address}",
            f"IBAN: {iban_display}",
            "",
            "COMPENSATION CLAIMS",
            "-" * 60,
        ]
        
        for i, delay in enumerate(self.delays, 1):
            trip = delay.trip
            lines.extend([
                f"\nTrip {i}:",
                f"  Train: {trip.train_number}",
                f"  Route: {trip.origin} → {trip.destination}",
                f"  Date: {trip.scheduled_departure.strftime('%Y-%m-%d')}",
                f"  Scheduled arrival: {trip.scheduled_arrival.strftime('%H:%M')}",
                f"  Actual arrival: {trip.actual_arrival.strftime('%H:%M') if trip.actual_arrival else 'N/A'}",
                f"  Delay: {delay.delay_minutes} minutes",
                f"  Ticket price: €{trip.ticket_price:.2f}",
                f"  Compensation ({delay.compensation_percentage}%): €{delay.compensation_amount:.2f}",
            ])
        
        lines.extend([
            "",
            "-" * 60,
            f"TOTAL COMPENSATION: €{self.total_amount:.2f}",
            "=" * 60,
            "",
            "Please process this reimbursement according to DB Fahrgastrechte.",
            "Bank transfer to the IBAN provided above.",
            "",
        ])
        
        return "\n".join(lines)
