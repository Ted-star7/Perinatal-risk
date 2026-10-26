"""Load the cohort data the notebooks and training read.

The cohorts are already built as processed CSVs (counts confirmed against the
proposal) and live, git-ignored, in data/processed/:

    {ke,tz}_perinatal.csv        19822 / 10980 rows
    {ke,tz}_perinatal_anc.csv    10590 / 5952  rows
    {ke,tz}_lbw.csv              4299  / 4626  rows

These come from the DHS recode files (GR/NR/BR/KR/IR) with missing codes
recoded and the v005 weight attached. Raw DHS files are never committed.

TODO (data custodian):
  - helper to read a cohort by name + country from contracts/cohort_config.yaml
  - re-run the stillbirth-rate gate (weighted KE rate = 15.1/1000)
  - optional: load the cleaned cohorts into the clean Postgres DB so the app and
    the eval portal can query them instead of reading CSVs.
"""
