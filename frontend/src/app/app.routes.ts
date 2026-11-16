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
  { path: 'clinic', canActivate: [authGuard], data: { mode: 'team' },
    loadComponent: () => import('./pages/clinic-account/clinic-account.component').then((m) => m.ClinicAccountComponent) },
  { path: 'account', canActivate: [authGuard], data: { mode: 'password' },
    loadComponent: () => import('./pages/clinic-account/clinic-account.component').then((m) => m.ClinicAccountComponent) },
  { path: 'join', data: { mode: 'join' },
    loadComponent: () => import('./pages/clinic-account/clinic-account.component').then((m) => m.ClinicAccountComponent) },
  { path: '', redirectTo: 'triage', pathMatch: 'full' },
  { path: '**', redirectTo: 'triage' },
];
