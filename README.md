# Smart Fitness Session Analyzer

Selected option: Option A - Smart Fitness Session Analyzer

- Student name: Miriam Throndsen
- Student number: 409902

This application continues the fitness analyzer from Assignment I. It reads participant profiles and fitness measurements from CSV files, checks the data, analyzes each session against the participant's personal baselines, and writes reports. The input data are simulated and the program is not a medical tool.

## Classes and design

- `ParticipantProfile` stores a participant ID and their baseline heart rate, skin response, and temperature.
- `FitnessObservation` represents one typed measurement from a session.
- `FitnessSessionAnalyzer` combines a profile with the session's observations. It calculates summaries, compares measurements with the profile, and assigns a classification with a reason.
- `RejectedRecord` stores the file, row, field, and reason for an input record that could not be used.
- `InvalidIdentifierError` and `InvalidRecordError` represent invalid IDs and invalid CSV data. `CsvFormatError` represents malformed CSV input and stores its row number.

The analyzer uses composition: it contains a `ParticipantProfile` and a list of `FitnessObservation` objects. Encapsulation is shown by keeping the summary-building logic inside `FitnessSessionAnalyzer`; `_build_summary` is an internal method. The profile and observation objects are frozen dataclasses, so their values cannot be changed after creation.

The custom errors also show inheritance: `InvalidIdentifierError` and `InvalidRecordError` inherit from `ValueError`, while `CsvFormatError` inherits from `InvalidRecordError`. `CsvFormatError` overrides `__init__` to keep the CSV row number as well as the error message. The analyzer classes do not use inheritance or overriding because there is only one analysis option in this application.

## Assumptions and classification rules

The participant's baseline values are assumed to represent their usual resting measurements. A signal quality below `0.6` makes that observation unusable. At least three usable observations are needed for a session classification. If there are fewer, the result is `insufficient_data` and no averages are reported.

For sessions with enough usable data, the program applies these rules in order:

1. Classify as `poor_quality` if at least 25% of the session's observations were rejected, or if average signal quality is below `0.6`.
2. Classify as `unusual` when average activity is at most `0.2` and at least one of these is true: heart rate is at least 30 bpm above baseline; skin response differs from baseline by at least `0.5`; temperature differs from baseline by at least `1.0`.
3. Classify as `recovery` when heart rate falls by at least 12 bpm from the first to the last observation, starts at least 10 bpm above baseline, and ends no more than 8 bpm above baseline.
4. Classify as `high_activity` when average activity is at least `0.68` and average heart rate is at least 35 bpm above baseline.
5. Classify as `moderate_activity` when average activity is at least `0.35` or average heart rate is at least 15 bpm above baseline.
6. Classify as `resting` when average activity is at most `0.2` and average heart rate is no more than 10 bpm above baseline. Other usable sessions are classified as `moderate_activity` with a mixed or transitional reason.

The summaries include average heart rate, skin response, temperature, activity, and signal quality; minimum and maximum heart rate and activity; and the differences between average heart rate, skin response, and temperature and their personal baselines. These thresholds are simple rules for the simulated assignment data, not medical thresholds.

## Installation and running

Use Python 3.10 or newer. The program uses only the Python standard library, so no packages need to be installed.

From the project folder, run:

```bash
python3 --version
python3 main.py \
  --profiles Assignment_II_Pack/data/option_a_fitness/participants.csv \
  --sessions Assignment_II_Pack/data/option_a_fitness/fitness_sessions.csv \
  --invalid-sessions Assignment_II_Pack/data/option_a_fitness/fitness_sessions_invalid.csv \
  --output output
```

The invalid-session option can be left out when `fitness_sessions_invalid.csv` is beside the regular session file. The program prints accepted and rejected row counts and the paths of the reports it creates. It replaces existing reports when run again.

## Example output

The official Option A data produce a completion message like this:

```text
Analysis complete: 25 accepted rows, 15 rejected rows.
Created report files:
- output/analysis_summary.csv
- output/analysis_report.txt
- output/rejected_records.txt
```

The readable report includes a result for each identifiable session, for example:

```text
Session FIT-2026-001 (P001)
  Classification: resting
  Data status: usable
  Observations: 6 usable, 0 rejected, 6 total
  Reason: activity and heart rate remained close to resting baseline
```

## Reports and rejected data

The program creates the output folder when needed:

- `analysis_summary.csv` contains one row for each identifiable session, including sessions with insufficient usable data.
- `analysis_report.txt` gives a readable result and reason for each session.
- `rejected_records.txt` lists each rejected file or row with its source file, row number, field, and reason.

The input CSV files are not changed. Rows without a valid session ID or a known participant cannot be included as a session summary; they are listed as rejected records instead.

## Known limitations

- The classification thresholds are simplified heuristics for simulated data. They have not been clinically validated and must not be used for health decisions.
- A session with fewer than three usable observations cannot receive an activity classification.
- This project implements Option A only. It does not analyze podcast recordings from Option B.
- The program assumes that the participant baselines supplied in the profile file are accurate and representative.

## Tests

Run the tests from the project folder:

```bash
python3 -m unittest -v
```