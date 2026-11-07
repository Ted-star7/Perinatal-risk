# Database setup — a walkthrough for the team

This is a teaching guide. By the end you'll understand **why** we use Docker,
how to create a table by hand with SQL, and what our seed script does and why.

> You only need this if you're working on the **dashboards / backend**. If you're
> doing **modeling**, you can skip it — the notebooks read CSVs directly.

---

## 0. The idea in one picture

```
Docker ──runs──► Postgres (the database server)
                     ▲
          TablePlus ─┘  (a window to look inside)
                     ▲
          seed script ─┘  (fills it with our data)
```

- **Postgres** stores the tables. **Docker** runs Postgres in a sealed box so
  everyone has the exact same setup — no "install Postgres on Windows" pain.
- **TablePlus** is just a viewer/editor to see and query the tables.
- **The seed script** loads our cohort data into the tables automatically.

---

## 1. Install Docker

- **Windows / Mac:** install **Docker Desktop** from docker.com → open it once so
  it's running (you'll see the whale icon).
- **Linux:** install **Docker Engine** (`sudo apt install docker.io`), then
  `sudo systemctl start docker`.

Check it works:
```bash
docker --version
docker compose version
```

Install **TablePlus** too (tableplus.com) — free tier is enough.

---

## 2. Start the database

From the project folder:
```bash
docker compose up -d app_db clean_db
docker compose ps        # both should say "Up"
```

What just happened: Docker read `docker-compose.yml`, downloaded Postgres, and
created two **empty** databases — `perinatal_app` (port 5432) and
`perinatal_clean` (port 5433). No tables yet.

---

## 3. Connect TablePlus

New connection → **PostgreSQL** →

| Field | app_db | clean_db |
|-------|--------|----------|
| Host | 127.0.0.1 | 127.0.0.1 |
| Port | 5432 | 5433 |
| User | app | readonly |
| Password | app | readonly |
| Database | perinatal_app | perinatal_clean |

Connect. Right now it's empty — let's change that.

---

## 4. Lesson: create a table BY HAND (so you understand what seeding automates)

In TablePlus, open the **SQL editor** on `perinatal_app` and run this. We'll make
a tiny `users` table from scratch:

```sql
-- CREATE TABLE defines the columns and their types
CREATE TABLE users (
    id      SERIAL PRIMARY KEY,   -- auto-numbering id
    name    TEXT,
    age     INTEGER,
    height  REAL                  -- a decimal number
);

-- INSERT puts rows in
INSERT INTO users (name, age, height) VALUES
    ('Amina', 29, 1.62),
    ('John', 34, 1.75);

-- SELECT reads them back
SELECT * FROM users;
```

You just created a table, added rows, and queried them. That's the whole idea of
a database: **define columns → insert rows → query**. When you're done playing:

```sql
DROP TABLE users;     -- removes it
```

**The point:** doing this by hand for our real data would mean writing a
`CREATE TABLE` with **40+ columns** and inserting **30,000 rows** by hand —
impossible. That's why we use a seed script.

---

## 5. The seed: let code do it

Our combined cohorts have thousands of rows and dozens of columns. The seed
script creates the tables **and** fills them in one go:

```bash
pip install -r db/requirements.txt      # once (use .venv/bin/pip on Kali)
python db/seed_combined.py
```

Under the hood it does, for each cohort, the same two steps you did by hand —
`CREATE TABLE` + `INSERT` — but automatically, reading the data straight from the
cleaned cohorts (`build_cohort()`). You'll see:

```
loaded combined_perinatal: 30,802 rows ...
combined tables in clean DB: ['combined_lbw', 'combined_perinatal', 'combined_perinatal_anc']
```

Refresh TablePlus (switch the schema dropdown to **public**) and the three
`combined_*` tables are there. **Why we seed instead of doing it by hand:** it's
repeatable (anyone runs one command), consistent (same data for everyone), and
safe to re-run (it replaces the tables).

---

## 6. End to end, recap

1. **Docker** gives everyone an identical Postgres with zero manual install.
2. `docker compose up` creates the empty databases.
3. **TablePlus** is how you look inside and run SQL.
4. A table is just **columns + rows** — you can make one by hand with
   `CREATE TABLE` / `INSERT`.
5. For real data, the **seed script** automates that at scale.
6. Later, the **dashboards** read from these tables (combined cohorts for stats,
   `model_metrics` for accuracy).

## Stop / reset

```bash
docker compose stop        # pause (keeps data)
docker compose down -v     # wipe everything for a fresh start
```
