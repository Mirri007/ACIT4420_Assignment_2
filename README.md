# Smart Fitness Session Analyzer

This program builds on the fitness analyzer from Assignment I. It reads participant and fitness data from CSV files, checks the records, classifies each session, and explains the result.

## Run the program

Run this command from the project folder:

```bash
python3 main.py \
  --profiles Assignment_II_Pack/data/option_a_fitness/participants.csv \
  --sessions Assignment_II_Pack/data/option_a_fitness/fitness_sessions.csv \
  --invalid-sessions Assignment_II_Pack/data/option_a_fitness/fitness_sessions_invalid.csv \
  --output output
```

The `--invalid-sessions` option is optional when the invalid file is next to the regular session file. The program then looks for a file named `fitness_sessions_invalid.csv` beside it.

The program prints how many rows it accepted and rejected, then lists the reports it created. Running it again replaces the reports with updated results.

## What the program checks

- Participant IDs must look like `P001`. Fitness session IDs must look like `FIT-2026-001`.
- CSV files must have the expected columns in the expected order. Values must be present, numeric where needed, and within the allowed ranges.
- A session must belong to a participant in `participants.csv`. Rows with unknown participants are rejected.
- A signal quality below `0.6` makes that observation unusable.
- Rejected rows are listed with their file name, row number, field, and reason.

## How sessions are classified

The program calculates average heart rate, skin response, temperature, activity, and signal quality. It also reports the lowest and highest heart rate and activity values, and compares heart rate, skin response, and temperature with the participant's personal baseline.

At least three usable observations are needed for a session classification. With fewer than three, the result is `insufficient_data`. If at least 25% of a session's observations are rejected, the result is `poor_quality`.

Other sessions use the Assignment I categories: `resting`, `moderate_activity`, `high_activity`, and `recovery`. A session can be marked `unusual` when activity is low and heart rate is at least 30 bpm above baseline, skin response differs from baseline by at least 0.5, or temperature differs by at least 1.0. The report explains which measurement triggered that result. These are simple rules for simulated assignment data, not medical thresholds. Changes in skin response or temperature during exercise do not by themselves change an activity classification.

## Reports

The program creates these files in the output folder:

- `analysis_summary.csv` contains one row for each session it can analyze, with the measurements, baseline differences, classification, and reason.
- `analysis_report.txt` gives a readable summary of each session.
- `rejected_records.txt` lists the rows that could not be used and why.

The program keeps the supplied CSV files unchanged. It uses only Python's standard library.

## Tests

Run the tests from the project folder:

```bash
python3 -m unittest -v
```