# Team & how we work

Group 13, six of us. Tedd runs the board and is the only one who merges into
`main`; everyone else branches and opens a pull request.

We split into two squads for the data stage: one cleans and explores the Kenya
DHS files, the other does Tanzania. Once the cohorts are in, we regroup around
the build (ml, backend, frontend).

| Person | Squad | GitHub |
|--------|-------|--------|
| Tedd (Bigted) | Tanzania · scrum master / integrator | `Ted-star7` |
| Jeremy | Kenya EDA | `mwangi54` |
| Eglen | Kenya EDA | `eglen-nyangasi` |
| dmwikya | Kenya EDA | `des-data` *(confirm)* |
| Caroline | Tanzania | _to add_ |
| (sixth) | Tanzania | `Kirukuu` *(confirm name)* |

Two usernames from the Ecosort repo still need a name against them: `des-data`
and `Kirukuu`. Once Tedd confirms who they are and Caroline sends her handle,
the table is final and the names go into `.github/CODEOWNERS`.

## The "shared truth" — `contracts/`

One folder every squad depends on, so we never disagree on definitions:

- `feature_spec.yaml` — every predictor: name, type, coding, DHS variable,
  missing codes.
- `cohort_config.yaml` — the one definition of each cohort + the build gate
  (reproduce the Kenya weighted stillbirth rate 15.1/1000).
- `features.py` — the single feature function training **and** the web app
  import, so a clinician's input is coded exactly like the training data.
- `openapi.yaml` — the API contract the frontend generates its client from.

**Rule: nobody edits `contracts/` quietly.** A change here affects everyone, so
it goes in its own PR, titled `contracts: ...`, and the integrator reviews it
before anything else merges.

## Who owns what

- `ml/` (notebooks + `src/`) — the DS work. KE squad builds the Kenya cohort;
  TZ squad builds Tanzania. Shared training/eval code lives in `ml/src/`.
- `backend/` — one backend owner leads; loads the trained artifact, serves the
  API. Never trains.
- `frontend/` — Angular: the clinical portal (input → result → feedback) and
  the eval portal (accuracy / calibration / SHAP graphs).
- `db/` — the data custodian owns the clean DB load; the app DB is the
  backend's.

## The daily loop (everyone)

```bash
git checkout main && git pull
git checkout -b feat/short-name        # or data/ fix/ model/ docs/
# work only inside your folder
git add -p && git commit -m "feat: ..."
git push -u origin feat/short-name
# open a PR into main, fill the template, request review
```

The integrator reviews, **squash-merges**, deletes the branch. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the full rules.

## Build order (each a merge gate)

1. Skeleton (done) → repo clones and the layout is agreed.
2. EDA + cleaning per squad → cleaned cohorts in the clean DB. Gate: KE
   stillbirth rate = 15.1/1000.
3. Baseline checklist + models → one versioned artifact. Gate: beats the
   checklist, validates on Tanzania.
4. Backend solid → API serves the artifact, logs every call, grounded LLM.
5. Eval portal → accuracy graphs.
6. Clinical portal → input → result → feedback (good / viable / unusable).
