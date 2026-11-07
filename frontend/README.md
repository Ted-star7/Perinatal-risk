# Frontend (Angular)

Two dashboards in one app:

- **clinician** (`/assess`) — the doctor enters pregnancy details and sees the
  risk ring, the drivers, and a follow-up note.
- **eval** (`/performance`) — the backoffice: model accuracy per cohort, read
  from the `model_metrics` table.

## Layout

```
src/
├── styles/_tokens.scss                     the warm palette (one source of colour)
└── app/
    ├── app.component.*                      shell + tab nav
    ├── app.routes.ts                        /assess and /performance
    └── pages/
        ├── clinician-dashboard/             standalone component (4 files)
        └── eval-dashboard/                  standalone component (4 files)
```

## Run

```bash
npm install     # once
npm start       # http://localhost:4200
```

The clinician scoring is a placeholder mirroring the EDA drivers. Once the
backend serves the real model it returns the score + SHAP and the page just
renders them.
