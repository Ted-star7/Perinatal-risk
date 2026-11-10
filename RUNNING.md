# Running the app (Windows)

The app has three parts: a **database**, a **backend API**, and the **frontend**.
The database and backend run in Docker; the frontend runs with the Angular CLI.

## 0. Install the tools (once)

1. **Docker Desktop** — download from docker.com, install.
   - It needs **WSL 2**. If the installer prompts, or Docker won't start:
     open **PowerShell as Administrator** and run `wsl --install`, then **restart**.
   - Open Docker Desktop and wait for the whale icon to say **running**.
2. **Node.js** (for the frontend) — download the LTS from nodejs.org, install.
3. **Angular CLI** — in a terminal: `npm install -g @angular/cli`
4. **Git** — git-scm.com.

Check they work:
```powershell
docker --version
node --version
ng version
```

## 1. Get the code and the data

```powershell
git clone https://github.com/Ted-star7/Perinatal-risk.git
cd Perinatal-risk
```
Put the shared DHS CSVs into `data\processed\` (Teddy sends the zip — unzip there).

## 2. Start the database + backend (Docker)

```powershell
docker compose up --build        # first time: builds the API image
```
This starts:
- `app_db`  — Postgres on port 5432 (clinics, doctors, predictions)
- `clean_db` — Postgres on port 5433 (the cohort data)
- `api`     — the FastAPI backend on **http://localhost:8000**

Leave this terminal running. Check the API: open http://localhost:8000/health
— it should say `{"status":"ok"}`.

## 3. Start the frontend (second terminal)

```powershell
cd Perinatal-risk\frontend
npm install        # once — downloads node_modules (not in git)
ng serve           # → http://localhost:4200
```

Open **http://localhost:4200** → **Register** your clinic → assess a patient →
**Save to clinic records** → the **History** tab lists your clinic's assessments.

## 4. Stop / start again

```powershell
docker compose stop        # stop the db + api, KEEP your data
docker compose up          # start again later (data is still there)
```

> **Do NOT run `docker compose down -v`** — the `-v` deletes the database
> volumes, so every registered clinic and saved assessment is wiped. Use
> `stop` to pause. Only use `down -v` when you deliberately want a clean slate.

## Ports at a glance

| Part | URL / port |
|------|-----------|
| Frontend | http://localhost:4200 |
| Backend API | http://localhost:8000 (docs at /docs) |
| app_db (Postgres) | localhost:5432 · user/pass `app`/`app` |
| clean_db (Postgres) | localhost:5433 · user/pass `readonly`/`readonly` |

## Loading the cohort data into clean_db (optional, for the eval side)

```powershell
pip install -r db\requirements.txt
python db\seed_combined.py
```
