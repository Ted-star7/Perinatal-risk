# data/

DHS files and the cohorts built from them are **licensed** — they are never
committed. Tedd shares them separately; drop them here locally.

Expected layout:

```
data/
└── processed/
    ├── ke_perinatal.csv        (19,822 rows)
    ├── ke_perinatal_anc.csv    (10,590 rows)
    ├── ke_lbw.csv              (4,299 rows)
    ├── tz_perinatal.csv        (10,980 rows)
    ├── tz_perinatal_anc.csv    (5,952 rows)
    └── tz_lbw.csv              (4,626 rows)
```

The notebooks read from `data/processed/`. Columns are documented in
`contracts/feature_spec.yaml`; cohort definitions and row counts in
`contracts/cohort_config.yaml`. Everything under `data/` except this file and
`.gitkeep` is git-ignored.
