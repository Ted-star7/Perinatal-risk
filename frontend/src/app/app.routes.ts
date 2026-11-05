import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'assess',
    loadComponent: () =>
      import('./pages/clinician-dashboard/clinician-dashboard.component').then(
        (m) => m.ClinicianDashboardComponent,
      ),
  },
  {
    path: 'performance',
    loadComponent: () =>
      import('./pages/eval-dashboard/eval-dashboard.component').then(
        (m) => m.EvalDashboardComponent,
      ),
  },
  { path: '', redirectTo: 'assess', pathMatch: 'full' },
];
