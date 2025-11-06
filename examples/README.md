# Examples

This directory contains example files for using the deutsch_verfahrn tracker.

## Example Trip JSON

`example_trip.json` - A sample trip format that can be used with:

```bash
deutsch-verfahrn add --json-file examples/example_trip.json
```

## Workflow Example

1. Add the example trip:
```bash
deutsch-verfahrn add --json-file examples/example_trip.json
```

2. Note the Trip ID from the output (e.g., `abc-123-def-456`)

3. Update with actual arrival time to simulate a delay:
```bash
deutsch-verfahrn update abc-123-def-456 --arrival "2024-01-15 15:30:00"
```

4. Check your balance:
```bash
deutsch-verfahrn balance --details
```

5. When you have enough balance, generate a claim:
```bash
deutsch-verfahrn generate --interactive
```
