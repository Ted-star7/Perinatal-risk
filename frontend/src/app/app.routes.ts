import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  {
    path: 'register',
    loadComponent: () =>
      import('./pages/register/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'triage',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/clinician-dashboard/clinician-dashboard.component').then(
        (m) => m.ClinicianDashboardComponent,
      ),
  },
  { path: 'assess', redirectTo: 'triage', pathMatch: 'full' },
  {
    path: 'history',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/clinic-history/clinic-history.component').then(
        (m) => m.ClinicHistoryComponent,
      ),
  },
  {
    path: 'performance',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/eval-dashboard/eval-dashboard.component').then(
        (m) => m.EvalDashboardComponent,
      ),
  },
  { path: '', redirectTo: 'triage', pathMatch: 'full' },
  { path: '**', redirectTo: 'triage' },
];
