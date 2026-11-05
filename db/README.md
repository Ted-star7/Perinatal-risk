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

## 2. Load the combined data into clean_db

Make sure the six source CSVs are in `data/processed/` first (see
`data/README.md`). Then install the loader deps once and seed the three
combined, cleaned, model-ready tables:

```bash
pip install -r db/requirements.txt      # or: .venv/bin/pip install -r db/requirements.txt
python db/seed_combined.py
```

You should see:

```
loaded combined_perinatal: 30,802 rows ...
loaded combined_lbw: 8,925 rows ...
combined tables in clean DB: ['combined_lbw', 'combined_perinatal', 'combined_perinatal_anc']
```

Re-running is safe — it replaces the tables. We load only the three combined
cohorts (the raw per-country tables aren't needed; `build_cohort()` reads the
source CSVs directly).

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
