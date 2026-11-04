# Frontend (Angular)

Two dashboards, one app:

- **clinician-dashboard** — the doctor enters pregnancy-time details and sees the
  risk ring, the drivers, and a follow-up note. (Warm, card-based UI.)
- **eval-dashboard** — the backoffice: model accuracy, calibration and SHAP per
  cohort, for the team and the presentation.

## Layout

```
src/
├── styles/
│   └── _tokens.scss                       # the warm palette (one source of colour)
└── app/
    ├── pages/
    │   ├── clinician-dashboard/           # dashboard 1 — standalone component
    │   │   └── clinician-dashboard.component.{ts,html,scss,spec.ts}
    │   └── eval-dashboard/                # dashboard 2 — standalone component
    │       └── eval-dashboard.component.{ts,html,scss,spec.ts}
    └── app.routes.ts                      # /assess and /performance
```

Each page is a **standalone component** with the four files (`ts`, `html`,
`scss`, `spec.ts`). Shared pieces (nav bar, card, risk ring) become components
under `app/shared/` as we grow.

## Scaffold the app (once)

```bash
cd frontend
ng new perinatal-ui --directory . --routing --style scss --standalone --skip-git
```
Then drop these `pages/` and `styles/` folders in, and:

1. `src/styles.scss`: `@use 'styles/tokens' as *;` and `body { background: var(--page-bg); }`
2. `src/app/app.routes.ts`:
   ```ts
   export const routes = [
     { path: 'assess', loadComponent: () =>
         import('./pages/clinician-dashboard/clinician-dashboard.component')
           .then(m => m.ClinicianDashboardComponent) },
     { path: 'performance', loadComponent: () =>
         import('./pages/eval-dashboard/eval-dashboard.component')
           .then(m => m.EvalDashboardComponent) },
     { path: '', redirectTo: 'assess', pathMatch: 'full' },
   ];
   ```
3. Load Inter + Tabler icons in `src/index.html` `<head>` (both on allowed CDNs).
4. `ng serve` → http://localhost:4200.

The clinician scoring is a placeholder mirroring the EDA drivers; once the
backend serves the real model it returns the score + SHAP and the page just
renders them.
