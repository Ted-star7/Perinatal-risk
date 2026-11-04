# Frontend (Angular)

Not scaffolded here — generate it with the Angular CLI so you get the exact
version you want, then commit. The folder is reserved so the mono-repo layout
and CODEOWNERS are already in place.

## One-time scaffold

```bash
npm install -g @angular/cli
cd frontend
ng new perinatal --directory . --routing --style scss --skip-git
npm install
```

## Folder layout to create under src/app/

```
core/api/        # client generated from ../../contracts/openapi.yaml
                 #   npx @openapitools/openapi-generator-cli generate \
                 #     -i ../contracts/openapi.yaml -g typescript-angular \
                 #     -o src/app/core/api
clinical/        # input form -> result (risk band + drivers) -> recommendation
                 #   -> feedback buttons (good / viable / unusable)
eval/            # dashboards: accuracy, calibration, SHAP, usage from /eval/metrics
```

## Why generate the client from the contract

`core/api` is generated from `contracts/openapi.yaml`, the same schema the
backend implements. Regenerate whenever the contract changes and the frontend
and backend can never drift. Do not hand-write API calls.

## Dev

```bash
ng serve           # http://localhost:4200  (API CORS already allows this)
```

The backend's stub model is live from day one, so you can build and test the
full input -> result -> feedback flow before the real model exists.

## Risk-assessment page (prototype on `teddy-frontend`)

`src/app/pages/risk-assessment/` holds the clinician console as a standalone
component (the four files: `.ts`, `.html`, `.scss`, `.spec.ts`), plus the warm
palette in `src/styles/_tokens.scss`.

To see it after `ng new` scaffolds the app:

1. `@use 'styles/tokens' as *;` at the top of `src/styles.scss`, and set
   `body { background: var(--page-bg); }`.
2. Add a route in `src/app/app.routes.ts`:
   ```ts
   { path: '', loadComponent: () =>
       import('./pages/risk-assessment/risk-assessment.component')
         .then(m => m.RiskAssessmentComponent) }
   ```
3. Load Tabler icons + Inter in `src/index.html` `<head>` (both on allowed CDNs).
4. `ng serve` → open http://localhost:4200.

The scoring in the component is a placeholder — once the backend is live it
returns the real score + SHAP drivers and this page just renders them.
