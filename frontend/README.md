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
