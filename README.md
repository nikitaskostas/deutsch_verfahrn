# deutsch_verfahrn

A Tracker of Public Transportation Lateness for Users in Germany

`deutsch_verfahrn` is a comprehensive system that monitors Deutsche Bahn (German Railway) trip delays, calculates compensation according to Fahrgastrechte (passenger rights), manages a virtual balance, and generates reimbursement forms.

## Features

- **Trip Tracking**: Import trips from DB smartphone app shared data
- **Delay Monitoring**: Automatically track arrival delays and calculate compensation
- **Virtual Balance**: Accumulate compensation amounts from multiple delayed trips
- **Compensation Calculation**: Follow official DB Fahrgastrechte rules:
  - 60-119 minutes delay: 25% ticket price refund
  - 120+ minutes delay: 50% ticket price refund
- **Alternative Transportation**: Suggest alternative routes during significant delays
- **Reimbursement Forms**: Auto-generate forms for DB compensation claims
- **Data Persistence**: SQLite database for tracking all trips and delays

## Installation

### From Source

```bash
git clone https://github.com/nikitaskostas/deutsch_verfahrn.git
cd deutsch_verfahrn
pip install -e .
```

### Requirements

- Python 3.8 or higher
- No external dependencies (uses standard library only)

## Usage

### Command Line Interface

The package provides a convenient CLI tool: `deutsch-verfahrn`

#### Add a New Trip

**Interactive mode:**
```bash
deutsch-verfahrn add
```

**From JSON file:**
```bash
deutsch-verfahrn add --json-file trip.json
```

Example JSON format:
```json
{
  "origin": "Berlin Hbf",
  "destination": "München Hbf",
  "scheduled_departure": "2024-01-15T10:00:00",
  "scheduled_arrival": "2024-01-15T14:00:00",
  "ticket_price": 89.90,
  "train_number": "ICE 123",
  "class": "2nd Class"
}
```

#### Update Trip with Actual Times

```bash
deutsch-verfahrn update TRIP_ID --arrival "2024-01-15 15:30:00"
```

This will:
- Calculate the delay
- Add compensation to virtual balance if applicable
- Suggest alternative transportation if delay is significant

#### Check Virtual Balance

```bash
deutsch-verfahrn balance
```

Show detailed delay history:
```bash
deutsch-verfahrn balance --details
```

#### Generate Reimbursement Form

**Interactive mode:**
```bash
deutsch-verfahrn generate --interactive
```

**Direct mode:**
```bash
deutsch-verfahrn generate \
  --name "Max Mustermann" \
  --address "Hauptstraße 1, 10115 Berlin" \
  --iban "DE89370400440532013000" \
  --output my_reimbursement.txt
```

### Python API

You can also use the package programmatically:

```python
from deutsch_verfahrn import LatenessTracker
from datetime import datetime

# Initialize tracker
tracker = LatenessTracker("my_tracker.db")

# Add a trip
trip_data = {
    "origin": "Berlin Hbf",
    "destination": "München Hbf",
    "scheduled_departure": "2024-01-15T10:00:00",
    "scheduled_arrival": "2024-01-15T14:00:00",
    "ticket_price": 89.90,
    "train_number": "ICE 123"
}
trip = tracker.add_trip_from_shared_data(trip_data)

# Update with actual arrival (90 minute delay)
actual_arrival = datetime(2024, 1, 15, 15, 30)
delay = tracker.update_trip_actual_times(
    trip.trip_id,
    actual_arrival=actual_arrival
)

if delay:
    print(f"Compensation: €{delay.compensation_amount:.2f}")
    print(f"Virtual balance: €{tracker.get_balance():.2f}")
    
    # Get alternative routes
    alternatives = tracker.suggest_alternatives(trip, delay.delay_minutes)
    for alt in alternatives:
        print(f"Alternative: {alt.mode} - arrives {alt.estimated_arrival}")

# Generate reimbursement form when balance is sufficient
if tracker.can_file_claim():
    form = tracker.generate_reimbursement_form(
        user_name="Max Mustermann",
        user_address="Hauptstraße 1, 10115 Berlin",
        user_iban="DE89370400440532013000"
    )
    tracker.export_form(form, "reimbursement.txt")
```

## How It Works

### 1. Trip Import
Import trip information from DB smartphone app or enter manually. The system stores:
- Route (origin/destination)
- Scheduled times
- Ticket price
- Train number and class

### 2. Delay Tracking
When you update the trip with actual arrival time:
- Calculates delay in minutes
- Checks if delay qualifies for compensation (≥60 minutes)
- Automatically calculates compensation percentage

### 3. Virtual Balance
Compensation amounts accumulate in a virtual balance:
- Minimum €4.00 required to file a claim
- Balance persists across sessions
- Tracks all associated delays

### 4. Alternative Transportation
For significant delays, the system suggests:
- Next ICE (high-speed) train
- IC (InterCity) trains
- Regional connections
- Taxi (for severe delays)

### 5. Reimbursement Form
When ready to claim:
- Generates official-format form
- Lists all compensable delays
- Includes user banking information
- Exports as text file for submission to DB

## German Railway Passenger Rights (Fahrgastrechte)

This system implements the official DB compensation rules:

| Delay Duration | Compensation |
|----------------|--------------|
| 60-119 minutes | 25% of ticket price |
| 120+ minutes   | 50% of ticket price |

**Note**: Minimum claim amount is €4.00

## Database Structure

The system uses SQLite to store:
- **trips**: All trip information
- **delays**: Delay events with compensation
- **balance**: Current virtual balance
- **reimbursement_forms**: Generated claim forms

Database location: `lateness_tracker.db` (customizable)

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

Or using unittest:

```bash
python -m unittest discover tests/
```

## Example Workflow

1. **After booking a trip**: Add it to the tracker
   ```bash
   deutsch-verfahrn add --json-file my_trip.json
   ```

2. **When trip completes**: Update with actual times
   ```bash
   deutsch-verfahrn update abc-123 --arrival "2024-01-15 15:30:00"
   ```

3. **Check balance regularly**:
   ```bash
   deutsch-verfahrn balance
   ```

4. **When balance ≥ €4**: Generate claim form
   ```bash
   deutsch-verfahrn generate --interactive
   ```

5. **Submit to Deutsche Bahn**: Use the generated form with DB Fahrgastrechte portal

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Disclaimer

This tool is for tracking and organizing compensation claims. Always verify the generated information before submitting to Deutsche Bahn. The developers are not responsible for any issues with submitted claims.
