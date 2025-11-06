"""
Command-line interface for the lateness tracker.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .tracker import LatenessTracker
from .models import Trip


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"€{amount:.2f}"


def print_trip_info(trip: Trip):
    """Print trip information."""
    print(f"\nTrip Information:")
    print(f"  ID: {trip.trip_id}")
    print(f"  Train: {trip.train_number}")
    print(f"  Route: {trip.origin} → {trip.destination}")
    print(f"  Class: {trip.trip_class.value}")
    print(f"  Ticket Price: {format_currency(trip.ticket_price)}")
    print(f"  Scheduled Departure: {trip.scheduled_departure.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Scheduled Arrival: {trip.scheduled_arrival.strftime('%Y-%m-%d %H:%M')}")
    if trip.actual_departure:
        print(f"  Actual Departure: {trip.actual_departure.strftime('%Y-%m-%d %H:%M')}")
    if trip.actual_arrival:
        print(f"  Actual Arrival: {trip.actual_arrival.strftime('%Y-%m-%d %H:%M')}")
        delay = trip.get_delay_minutes()
        if delay > 0:
            print(f"  Delay: {delay} minutes")


def cmd_add_trip(args):
    """Add a new trip to the tracker."""
    tracker = LatenessTracker(args.db)
    
    # Read trip data
    if args.json_file:
        with open(args.json_file, 'r') as f:
            data = json.load(f)
    else:
        # Interactive mode
        print("Enter trip details:")
        data = {
            "origin": input("Origin: "),
            "destination": input("Destination: "),
            "scheduled_departure": input("Scheduled departure (YYYY-MM-DD HH:MM): "),
            "scheduled_arrival": input("Scheduled arrival (YYYY-MM-DD HH:MM): "),
            "ticket_price": float(input("Ticket price (EUR): ")),
            "train_number": input("Train number: "),
            "class": input("Class (1st/2nd): ")
        }
    
    trip = tracker.add_trip_from_shared_data(data)
    print_trip_info(trip)
    print(f"\n✓ Trip added successfully!")


def cmd_update_trip(args):
    """Update trip with actual arrival/departure times."""
    tracker = LatenessTracker(args.db)
    
    actual_arrival = None
    if args.arrival:
        actual_arrival = datetime.fromisoformat(args.arrival)
    
    actual_departure = None
    if args.departure:
        actual_departure = datetime.fromisoformat(args.departure)
    
    delay = tracker.update_trip_actual_times(
        args.trip_id,
        actual_departure=actual_departure,
        actual_arrival=actual_arrival
    )
    
    if delay:
        print(f"\n⚠️  Delay detected!")
        print(f"  Delay: {delay.delay_minutes} minutes")
        print(f"  Compensation: {format_currency(delay.compensation_amount)} ({delay.compensation_percentage}%)")
        print(f"  Added to virtual balance")
        
        # Show alternatives if significant delay
        trip = tracker._load_trip(args.trip_id)
        if trip and delay.delay_minutes >= 30:
            alternatives = tracker.suggest_alternatives(trip, delay.delay_minutes)
            if alternatives:
                print(f"\n💡 Alternative transportation options:")
                for i, alt in enumerate(alternatives, 1):
                    print(f"  {i}. {alt.mode}")
                    print(f"     Arrival: {alt.estimated_arrival.strftime('%H:%M')}")
                    if alt.additional_cost > 0:
                        print(f"     Cost: {format_currency(alt.additional_cost)}")
                    print(f"     {alt.description}")
    else:
        print(f"\n✓ Trip updated (no compensation applicable)")


def cmd_balance(args):
    """Show current virtual balance."""
    tracker = LatenessTracker(args.db)
    
    balance = tracker.get_balance()
    delays = tracker.get_all_delays()
    
    print(f"\n💰 Virtual Balance: {format_currency(balance)}")
    print(f"   Total delays: {len(delays)}")
    
    if tracker.can_file_claim():
        print(f"   ✓ You can file a reimbursement claim!")
    else:
        threshold = tracker.virtual_balance.threshold_for_claim
        remaining = threshold - balance
        print(f"   Need {format_currency(remaining)} more to file a claim (min: {format_currency(threshold)})")
    
    if args.details and delays:
        print(f"\n📋 Delay History:")
        for delay in delays[:10]:  # Show last 10
            print(f"\n  {delay.trip.train_number} - {delay.trip.origin} → {delay.trip.destination}")
            print(f"  Date: {delay.timestamp.strftime('%Y-%m-%d')}")
            print(f"  Delay: {delay.delay_minutes} min | Compensation: {format_currency(delay.compensation_amount)}")


def cmd_generate_form(args):
    """Generate reimbursement form."""
    tracker = LatenessTracker(args.db)
    
    if not tracker.can_file_claim():
        print(f"\n❌ Insufficient balance to file a claim")
        print(f"   Current balance: {format_currency(tracker.get_balance())}")
        print(f"   Minimum required: {format_currency(tracker.virtual_balance.threshold_for_claim)}")
        sys.exit(1)
    
    # Get user information
    if args.interactive:
        print("Enter your details for reimbursement:")
        user_name = input("Full name: ")
        user_address = input("Address: ")
        user_iban = input("IBAN: ")
    else:
        user_name = args.name
        user_address = args.address
        user_iban = args.iban
    
    form = tracker.generate_reimbursement_form(user_name, user_address, user_iban)
    
    if form:
        output_file = args.output or f"reimbursement_{form.form_id[:8]}.txt"
        tracker.export_form(form, output_file)
        
        print(f"\n✓ Reimbursement form generated!")
        print(f"  Form ID: {form.form_id}")
        print(f"  Amount: {format_currency(form.total_amount)}")
        print(f"  Saved to: {output_file}")
        print(f"\n📄 Preview (IBAN masked for security):")
        print("=" * 60)
        print(form.export_to_text(mask_sensitive=True))
        print("\n⚠️  Note: The actual file contains the full IBAN for submission.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Deutsche Bahn Transportation Lateness Tracker"
    )
    parser.add_argument(
        "--db",
        default="lateness_tracker.db",
        help="Database file path (default: lateness_tracker.db)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add trip command
    add_parser = subparsers.add_parser("add", help="Add a new trip")
    add_parser.add_argument("--json-file", help="JSON file with trip data")
    
    # Update trip command
    update_parser = subparsers.add_parser("update", help="Update trip with actual times")
    update_parser.add_argument("trip_id", help="Trip ID")
    update_parser.add_argument("--arrival", help="Actual arrival time (YYYY-MM-DD HH:MM:SS)")
    update_parser.add_argument("--departure", help="Actual departure time (YYYY-MM-DD HH:MM:SS)")
    
    # Balance command
    balance_parser = subparsers.add_parser("balance", help="Show virtual balance")
    balance_parser.add_argument("--details", action="store_true", help="Show delay history")
    
    # Generate form command
    form_parser = subparsers.add_parser("generate", help="Generate reimbursement form")
    form_parser.add_argument("--name", help="Your full name")
    form_parser.add_argument("--address", help="Your address")
    form_parser.add_argument("--iban", help="Your IBAN")
    form_parser.add_argument("--output", help="Output file path")
    form_parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == "add":
        cmd_add_trip(args)
    elif args.command == "update":
        cmd_update_trip(args)
    elif args.command == "balance":
        cmd_balance(args)
    elif args.command == "generate":
        cmd_generate_form(args)


if __name__ == "__main__":
    main()
