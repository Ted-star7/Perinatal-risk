# Database setup — step-by-step for the team

A complete walkthrough: install the tools, start the database, create a test
table by hand to learn SQL, then load our real data with the seed. Follow it
top to bottom.

> Only needed if you're working on the **dashboards**. Modeling people read CSVs
> and can skip all of this.

---

## About the passwords (read this first)

Every teammate runs **their own** database on **their own computer** (localhost).
Nothing is shared over the internet, so the passwords are **not secret** — they
are baked into `docker-compose.yml` and are the same for everyone:

| Database | Host | Port | User | Password | DB name |
|----------|------|------|------|----------|---------|
| app_db | 127.0.0.1 | 5432 | `app` | `app` | `perinatal_app` |
| clean_db | 127.0.0.1 | 5433 | `readonly` | `readonly` | `perinatal_clean` |

So "what password do I give them?" → just tell them **`app`** and **`readonly`**.
They're local dev credentials, not a real secret.

---

## Step 1 — install the tools

1. **Docker**
   - Windows / Mac: download **Docker Desktop** from docker.com, install, and
     **open it once** (wait for the whale icon to say "running").
   - Linux: `sudo apt install docker.io` then `sudo systemctl start docker`.
2. **TablePlus** — download from tableplus.com (free tier is fine).

Check Docker works, in a terminal:
```bash
docker --version
docker compose version
```

---

## Step 2 — get the project and start the database

In a terminal, go to the project folder (wherever you cloned it):
```bash
cd ~/perinatal-risk          # <-- wherever your clone is
docker compose up -d app_db clean_db
docker compose ps            # both lines should say "Up"
```

What this did: Docker downloaded Postgres and created two **empty** databases —
`perinatal_app` and `perinatal_clean`. There are no tables yet; we add those next.

---

## Step 3 — create a connection in TablePlus (click by click)

1. Open **TablePlus**.
2. Click **Create a new connection…** (or the **+** in the bottom-left).
3. In the list of database types, choose **PostgreSQL**, then **Create**.
4. Fill in the fields exactly:
   - **Name:** `Perinatal clean` (any label you like)
   - **Host:** `127.0.0.1`
   - **Port:** `5433`
   - **User:** `readonly`
   - **Password:** `readonly`
   - **Database:** `perinatal_clean`
   - Leave **SSH** / **SSL** off — it's local.
5. Click **Test** → it should turn green.
6. Click **Connect**.

You're now looking at an empty database. Make a second connection the same way
for `perinatal_app` using port **5432**, user **app**, password **app**, database
**perinatal_app** — that's where predictions and model results live.

---

## Step 4 — learn SQL by making a table by hand

Before the automated seed, make one table yourself so you see what's happening.
In TablePlus, open the **SQL editor** (the `>_` icon) on `perinatal_app` and run:

```sql
CREATE TABLE users (
    id      SERIAL PRIMARY KEY,
    name    TEXT,
    age     INTEGER,
    height  REAL
);

INSERT INTO users (name, age, height) VALUES
    ('Amina', 29, 1.62),
    ('John', 34, 1.75);

SELECT * FROM users;
```

Put the cursor in a statement and press **Cmd/Ctrl + Enter** to run it. You just:
- **created** a table (defined its columns),
- **inserted** two rows,
- **selected** them back.

That's all a database is: columns + rows. Clean up when done:
```sql
DROP TABLE users;
```

**The lesson:** doing this by hand for our real data means a `CREATE TABLE` with
**40+ columns** and inserting **30,000 rows** — nobody types that. So we automate
it with a seed.

---

## Step 5 — seed the real data

Back in the terminal, in the project folder:
```bash
pip install -r db/requirements.txt       # once (use .venv/bin/pip on Kali)
python db/seed_combined.py
```

You'll see:
```
loaded combined_perinatal: 30,802 rows ...
combined tables in clean DB: ['combined_lbw', 'combined_perinatal', 'combined_perinatal_anc']
```

The script did the exact `CREATE TABLE` + `INSERT` you did by hand — but for all
three cohorts, automatically, reading from the cleaned data. **That's why we
seed:** it's one command, identical for everyone, and safe to re-run (it replaces
the tables).

---

## Step 6 — see it

In TablePlus, click the refresh icon and switch the **schema** dropdown
(bottom-left) to **public**. The three `combined_*` tables now appear. Click one
→ **Data** tab to browse rows, **Structure** tab for its columns.

---

## Recap (the end-to-end)

1. **Docker** runs Postgres identically for everyone — no manual DB install.
2. `docker compose up` creates the empty databases.
3. **TablePlus** connects to them so you can look inside and run SQL.
4. A table is **columns + rows**; you can make one with `CREATE TABLE` / `INSERT`.
5. The **seed** does that at scale from our real data.
6. The **dashboards** then read these tables.

## Stop / reset

```bash
docker compose stop        # pause, keeps data
docker compose down -v     # wipe for a clean start, then re-seed
```
