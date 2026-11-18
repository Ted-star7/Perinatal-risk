# Running the app locally

The app has three parts: a **database**, a **backend API**, and the **frontend**.
The database and backend run in Docker; the frontend runs with the Angular CLI.

## 0. Install the tools (once)

1. **Docker Desktop** — download from docker.com, install.
   - It needs **WSL 2**. If the installer prompts, or Docker won't start:
     open **PowerShell as Administrator** and run `wsl --install`, then **restart**.
   - Open Docker Desktop and wait for the whale icon to say **running**.
2. **Node.js 24.18 or newer 24.x** (for the frontend) — install from nodejs.org.
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
- `app_db` — one Postgres database on port 5432 holding **everything**:
  clinics, doctors, predictions, the combined cohort tables, and the metrics.
- `api` — the FastAPI backend on **http://localhost:8000**

On startup the API **auto-loads** the combined cohort tables (`combined_*`) into
the database, as long as the CSVs are in `data\processed\`. No manual seed step.

Leave this terminal running. Check the API: open http://localhost:8000/ready. It checks the database and the two serving models: perinatal and low birth weight.
`/health` checks whether the API process is alive.

## 3. Start the frontend (second terminal)

```powershell
cd Perinatal-risk\frontend
npm ci             # install the committed dependency versions
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
| Database (Postgres) | localhost:5432 · user/pass `app`/`app` · db `perinatal_app` |

View everything in TablePlus: connect to `127.0.0.1:5432`, user/pass `app`/`app`,
database `perinatal_app`, schema **public** — you'll see the clinics, doctors,
predictions, and the `combined_*` cohort tables all in one place.

## Local frontend startup

After pulling dependency or builder changes, stop the frontend with `Ctrl+C`,
run `npm ci` inside `frontend/`, then restart with `npm start` or `ng serve`.
The project uses `@angular/build` for development, production builds and tests.
`Application bundle generation complete` followed by `Watch mode enabled`
means the development server started successfully.

Local assessments use the joblib releases installed in the API Docker image.
Keep the API running and check `http://localhost:8000/ready`. The authenticated
`/model-releases` API describes the installed files. The hidden `/performance`
page reads the approved research comparison from `/evaluation-metrics`; startup
installs that versioned comparison in both local and hosted databases. It is
separate from the models used for ongoing-pregnancy assessment.

The optional command below publishes packaged antenatal reports to the legacy
`/metrics` store, without replacing the approved performance comparison:

```bash
docker compose exec api python -m ml.src.train_antenatal_models --publish-local
```

This publishes the nine packaged evaluation rows locally. It does not retrain
the models or update the hosted database.

## Trained models and clinician results

The assessment now calls `POST /assess` to calculate a result and `POST /predict`
to save it. Results include the perinatal score, secondary low birth weight
score, and the project's checklist baseline. Saved records include both scores,
model hashes and checklist findings. Earlier records remain readable.

A fresh checkout includes the packaged model release; training is optional for
running assessments. To retrain, use Python 3.12 or 3.13 and install
`ml/requirements.txt` in your virtual environment. Run the antenatal trainer from
the repository root, validate and package its outputs, then rebuild the API and
publish the evaluation metrics.

```bash
python -m ml.src.train_antenatal_models
python -m ml.src.validate_country
python -m ml.src.package_release --output backend/models/antenatal-release.tar.gz
docker compose up -d --build
docker compose exec api python -m ml.src.train_antenatal_models --publish-local
cd frontend
npm start
```

Open http://localhost:4200 and register a clinic or sign in with an existing local
account. The database persists between runs. Open `/performance` directly after signing in to see local evaluation metrics
and the actual serving releases. Its navigation link is hidden during clinician
testing. Signed-in testers can still open this route, as requested. `--publish-local` updates only http://localhost:8000/metrics.

The evaluation page presents the approved original notebook comparison, selected
by mean grouped training CV PR-AUC: perinatal GB, LBW GB, ANC LR. Startup installs
this versioned nine-row set in `approved_model_metrics` once and replaces the
active legacy `model_metrics` values. Previous submissions are retained in
`model_metrics_archive`. `/evaluation-metrics` reads the approved database set,
so later unversioned notebook submissions cannot mix or overwrite its figures.
The approved set is aggregate evaluation data, not executed notebook output.
The ongoing-pregnancy input form and its fitted model releases remain separate.
The performance page shows only the approved research comparison; release metadata
is available through the authenticated API for internal checks.

The antenatal trainer compares logistic regression, random forest and gradient
boosting for each cohort using five grouped training folds. It selects by mean
training average precision, then fits grouped sigmoid calibration and evaluates
held-out records. The predictor definitions are in `ml/src/antenatal.py`.
Age is measured when pregnancy began, estimated in the training data as
`floor((p3 - p20 - v011) / 12)`. The common predictors are age at pregnancy start,
previous live births, first pregnancy, previous stillbirth, previous loss and
multiple pregnancy. LBW additionally uses education. Completed-pregnancy ANC
measures and outcome-to-outcome intervals are excluded from these releases.
The current history checklist uses age at pregnancy start, parity, multiple
pregnancy and previous stillbirth. Evaluation compares equal numbers of flags.
Exports are under `ml/models/antenatal/<cohort>/selected.joblib` and `selected.json`.

The original nine modeling notebooks and `select_models` / `calibrate_models`
commands reproduce the historical research recipes under `ml/models/<cohort>/`.
These historical releases have a different input definition. The clinician API
checks the antenatal prediction context before loading a serving release.

For the historical `ml.src.select_models` exporter, running without `--refresh`
reproduces the algorithm selected in the existing shared `/metrics` store. This mode honors a single `is_best` flag,
or the highest recorded PR-AUC when no winner is marked. `METRICS_API_URL` sets
that source API. For an intentional shared dashboard view, set
`METRICS_SOURCE_URL=https://perinatal-api.onrender.com/metrics` before starting
Docker. The default local dashboard uses its own database.

The selected exports require scikit-learn 1.9.1, matching their training version.
The API rejects incompatible model versions and invalid outputs. Local training
exports under `ml/models/` stay git-ignored; the verified compressed release under
`backend/models/` is committed. Keep each release's joblib files together with
their JSON reports.

The clinician assessment uses the general perinatal model as its primary result
and the LBW model as its secondary result. The ANC cohort is retained for research
comparison with the same antenatal predictor definitions. Unknown education makes
LBW unavailable while the primary assessment remains available.
The UI sends `age_at_start` explicitly. Earlier API clients need this new field
when calculating a new assessment. Previously saved results remain readable.
Older opted-in drafts are cleared because their age field used a different definition.

The published PR-AUC value is average precision. ROC-AUC measures ranking.
The reports include calibration curves, Brier scores, outcome rates and
survey-weighted country results. `country_validation.json` reports Kenya-only
selection and calibration evaluated on Tanzania for the antenatal feature set.
Independent prospective clinical validation and clinical cutoffs are pending.

## Packaged models and hosted builds

`backend/models/antenatal-release.tar.gz` contains the verified serving models,
evaluation reports and a SHA-256 manifest. The Docker build verifies and installs
this release, so a fresh private-repository checkout can run predictions.
Licensed CSVs and local training exports are excluded from the Docker context.

After training a new release, regenerate the package and rebuild the API.

```bash
python -m ml.src.package_release --output backend/models/antenatal-release.tar.gz
docker compose up -d --build api
```

The optional HTTPS `*_MODEL_URL` / `*_MODEL_SHA256` variables can override the
packaged models. Mounted `*_MODEL_PATH` settings support direct API setups.
Restart the API to activate a new model release. Saved results record its hash.

The notebook metrics client reads `METRICS_API_URL` and `METRICS_KEY` on every
call. Set the publishing key for the destination API before calling
`db.metrics.save_metrics`. A rejected or unconfirmed submission raises an error
so a notebook can retry. Successful submissions update `model_metrics`.

Existing database tables gain nullable `assessment` and `request_id` columns on
startup. A unique index prevents duplicate saves when the UI retries the same
request. The database role needs permission to alter the predictions table.

Run the focused backend regression tests after installing backend requirements
and `httpx` in your environment.

```bash
PYTHONPATH=backend:. python -m unittest discover -s backend/tests -v
```

## Secrets, clinic accounts and draft recovery

Copy `.env.example` to `.env` and set distinct random `JWT_SECRET` and
`METRICS_KEY` values before starting Docker. Generate each with
`python -c "import secrets; print(secrets.token_urlsafe(48))"`. Keep `.env` private.
Export the same `METRICS_KEY` in your terminal before publishing local metrics.
Production requires a persistent strong signing secret. Rotating it requires
users to sign in again.

Clinic owners can invite colleagues from the account menu and deactivate their
access. Invitation links expire after 48 hours and are single-use. The owner
shares the link with the intended colleague. Change password is in the account
menu. Changing a password invalidates previous sessions.

The optional draft checkbox keeps an assessment in this browser tab for up to
two hours. Saving or explicitly signing out clears it. The save operation
preserves the assessment that the clinician reviewed, even if a model changes
between calculation and saving. Clinic records support search and pagination.

## Interface image

The login and assessment pages use the existing project image
`frontend/public/mother-baby.png`. Registration uses
`frontend/public/registration-maternity.webp`, a compressed copy of the portrait
previously produced with the built-in image generation tool. Its final prompt follows.

> Use case: photorealistic-natural. Asset type: portrait photograph for an East African maternal health clinician portal sign-in page. Create an elegant editorial maternity portrait of an adult Kenyan or Tanzanian Black woman in her early thirties, pregnant, wearing a modest flowing warm ivory maternity dress with a soft sage overshirt, seated comfortably in three-quarter profile with one hand resting naturally on her belly. A quiet, confident smile, natural textured hair, authentic skin texture and proportions. Minimal warm sand and ivory studio background, soft daylight from the side, muted terracotta and olive undertones. Premium healthcare editorial photography, calm, dignified and welcoming. Vertical portrait composition, head and hands fully in frame, generous clean space above and beside the subject for a responsive crop. Single subject, no text, no graphic UI, no graphs, no medical equipment, no logos, no watermark.

Typography and icons are served from local assets with their licenses.

## Birth outcomes and clinical follow-up

After saving an assessment, open **Clinic records**, search the patient reference,
and select **Add outcome or notes**. Enter the follow-up date and information
source. You can record notes before the birth with **Not yet known**, then update
with the birth date, measured birth weight in grams, and survival status.
For a death after live birth, record age at death in completed days (0 means the
birth day). For multiples, choose a baby number and keep that number consistent
with the maternity register. Record each baby separately.

The API creates the `birth_outcomes` table automatically at startup for both new
and existing databases, using the serialized migration transaction (version 5).
Existing assessments are preserved. Each saved change appends a revision with
clinician ID, timestamp, baby number and assessment ID. History shows the latest
revision per baby; **View follow-up history** shows all revisions. Conflicting
edits return HTTP 409 rather than overwriting another clinician's update.

From the repository root, rebuild the backend to apply the schema:

```bash
docker compose up -d --build
```

Synthetic examples are **opt-in and development-only**. First register a local
clinic, find its clinician ID in `/session` or TablePlus (`doctors.id`), then run
(replace `1` with that ID):

```bash
docker compose exec api python -m app.seed_followups --doctor-id 1 --demo
```

The idempotent seeder creates three clearly marked `DEMO-FOLLOWUP-*` records
with invented outcomes, including a low-weight baby and a death after birth.
No prediction model is run for these examples. They have `inputs.synthetic=true`
and must be excluded from evaluation and training. It never runs automatically
and refuses production mode. Real clinic data should not be replaced by demos.

API endpoints (signed-in clinicians, own clinic only):

- `POST /predictions/{id}/outcomes`: append an outcome revision. Send
  `expected_version: 0` for the first entry for a baby; send its current version
  for later edits. Dates and known-outcome consistency are validated.
- `GET /predictions/{id}/outcomes`: full revision history.
- `GET /history`: includes latest `outcomes` per baby.

These observations do not automatically retrain or change live model metrics.
Before using them for model development, review source quality and completeness,
resolve corrections and duplicate pregnancies/assessments, exclude synthetic data,
and avoid splitting the same mother or pregnancy across training and evaluation.
For the project's targets, measured weight below 2500 g supplies the LBW label;
stillbirth or death at age 0–6 completed days supplies the perinatal event label.
An alive follow-up before seven completed days cannot establish a negative
perinatal label. Missing weight/outcome remains unknown, never a negative result.
The app stores the observations; it does not yet create training labels or fit
new models from them.

Care and referral notes provide useful context, but an improved outcome after
an alert does not prove the alert caused that improvement. Changed care can also
change the relationship between an initial prediction and the observed outcome.
Reviewed data, appropriate evaluation and an approved new model release are
needed before any update to clinical inference.
