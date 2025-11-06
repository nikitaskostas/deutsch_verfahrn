"""
Alternative transportation suggester for delayed trips.
"""

from datetime import timedelta
from typing import List

from .models import Trip, AlternativeRoute


class AlternativeTransportSuggester:
    """Suggests alternative transportation when delays occur."""
    
    def get_alternatives(
        self, 
        trip: Trip, 
        current_delay_minutes: int
    ) -> List[AlternativeRoute]:
        """
        Generate alternative transportation suggestions based on delay.
        
        Args:
            trip: Current trip with delay
            current_delay_minutes: Current delay in minutes
            
        Returns:
            List of alternative routes sorted by estimated arrival time
        """
        alternatives = []
        
        # Get the expected arrival with current delay
        delayed_arrival = trip.scheduled_arrival + timedelta(minutes=current_delay_minutes)
        
        # Suggest faster train options
        if current_delay_minutes >= 20:
            # ICE (high-speed) alternative
            ice_alternative = AlternativeRoute(
                mode="ICE (High-Speed Train)",
                estimated_arrival=trip.scheduled_arrival + timedelta(minutes=10),
                additional_cost=0.0,  # Covered by DB rights
                description=f"Next ICE train from {trip.origin} to {trip.destination}"
            )
            if ice_alternative.is_faster(delayed_arrival):
                alternatives.append(ice_alternative)
            
            # IC (intercity) alternative
            ic_alternative = AlternativeRoute(
                mode="IC (InterCity Train)",
                estimated_arrival=trip.scheduled_arrival + timedelta(minutes=15),
                additional_cost=0.0,
                description=f"Next IC train from {trip.origin} to {trip.destination}"
            )
            if ic_alternative.is_faster(delayed_arrival):
                alternatives.append(ic_alternative)
        
        # Suggest regional trains for moderate delays
        if current_delay_minutes >= 30:
            regional_alternative = AlternativeRoute(
                mode="Regional Train",
                estimated_arrival=trip.scheduled_arrival + timedelta(minutes=25),
                additional_cost=0.0,
                description=f"Alternative regional connection to {trip.destination}"
            )
            if regional_alternative.is_faster(delayed_arrival):
                alternatives.append(regional_alternative)
        
        # Suggest taxi for severe delays and short distances
        if current_delay_minutes >= 60:
            # Estimate taxi cost (rough estimate: 2 EUR/km base)
            taxi_time = max(30, current_delay_minutes // 2)
            taxi_alternative = AlternativeRoute(
                mode="Taxi",
                estimated_arrival=trip.scheduled_arrival + timedelta(minutes=taxi_time),
                additional_cost=50.0,  # Estimated cost, may be reimbursed
                description=f"Taxi to {trip.destination} (costs may be reimbursed if delay > 60 min)"
            )
            if taxi_alternative.is_faster(delayed_arrival):
                alternatives.append(taxi_alternative)
        
        # Sort by estimated arrival time
        alternatives.sort(key=lambda x: x.estimated_arrival)
        
        return alternatives
