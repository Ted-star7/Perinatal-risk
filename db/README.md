# Database (local, via Docker)

Two Postgres databases run in Docker:

- **clean_db** (port **5433**) — the cleaned cohorts, loaded from `data/processed/`.
- **app_db** (port **5432**) — predictions, recommendations, feedback (filled later
  by the backend; empty for now).

You only need Docker installed. No local Postgres required.

## 1. Start the databases

```bash
docker compose up -d app_db clean_db
```

Check they're running:

```bash
docker compose ps
```

## 2. Load the cohort data into clean_db

Make sure the six CSVs are in `data/processed/` first (see `data/README.md`).
Then install the loader deps once and run the seed:

```bash
pip install -r db/requirements.txt      # or: .venv/bin/pip install -r db/requirements.txt
python db/seed.py
```

You should see all six cohorts load with their row counts:

```
loaded ke_perinatal: 19,822 rows ...
loaded tz_lbw: 4,626 rows ...
tables in clean DB: ['ke_lbw', 'ke_perinatal', 'ke_perinatal_anc', 'tz_lbw', 'tz_perinatal', 'tz_perinatal_anc']
```

### Optional: load the combined, cleaned, model-ready data

`seed.py` loads the six raw cohort CSVs. To also load the **combined** data
(KE+TZ concatenated, cleaned, with the 80/20 split column) — the modeling-ready
version the backoffice reads — run:

```bash
python db/seed_combined.py
```

This creates three tables: `combined_perinatal`, `combined_perinatal_anc`,
`combined_lbw`. It calls `ml/src/dataset.build_cohort()`, so it reflects the
latest cleaning automatically.

Re-running `seed.py` is safe — it replaces the tables.

## 3. View it in TablePlus

New connection → PostgreSQL → fill in:

| Field | clean_db | app_db |
|-------|----------|--------|
| Host | 127.0.0.1 | 127.0.0.1 |
| Port | **5433** | **5432** |
| User | readonly | app |
| Password | readonly | app |
| Database | perinatal_clean | perinatal_app |

Connect, open the database, and you'll see the six cohort tables under
**public**. Double-click any to browse rows or run SQL.

## Stop / reset

```bash
docker compose stop            # stop (keeps data)
docker compose down            # stop and remove containers (keeps data volume)
docker compose down -v         # also wipe the data volume (fresh start)
```
