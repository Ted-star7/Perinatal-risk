# Local PostgreSQL database

Docker Compose runs PostgreSQL 16 in the `app_db` service. It stores clinic
accounts, assessment records, model metrics and available combined cohort tables.

```bash
docker compose up -d --build
docker compose ps
```

The API seeds missing combined cohort tables from `data/processed/` on startup.
Existing clinic and patient records persist in the Docker volume.

## TablePlus connection

Create a PostgreSQL connection using these local development settings.

| Field | Value |
|---|---|
| Host | 127.0.0.1 |
| Port | 5432 |
| User | app |
| Password | app |
| Database | perinatal_app |
| Schema | public |

Tables include `clinics`, `doctors`, `predictions`, `model_metrics` and the three
`combined_*` tables when the licensed data is present.

```bash
docker compose stop
docker compose up -d
```

`docker compose down -v` deletes the volume and all stored records.
See [RUNNING.md](../RUNNING.md) for model exports, secrets and frontend startup.
