import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { tap } from 'rxjs';
import { ApiService } from './api.service';
import { LoginBody, RegisterBody, Session } from './models';

const KEY = 'perinatal.session';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private api = inject(ApiService);
  private router = inject(Router);
  readonly session = signal<Session | null>(this.restore());
  readonly isLoggedIn = computed(() => this.session() !== null && this.validToken(this.session()!.token));

  constructor() {
    queueMicrotask(() => {
      if (!this.isLoggedIn()) return;
      this.api.session().subscribe({
        next: (verified) => {
          const current = this.session();
          if (current) this.store({ ...current, is_owner: verified.is_owner });
        },
        error: () => {},
      });
    });
  }

  private validToken(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      return typeof payload.exp === 'number' && payload.exp * 1000 > Date.now();
    } catch { return false; }
  }

  private restore(): Session | null {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return null;
      const session = JSON.parse(raw) as Session;
      if (typeof session.token !== 'string' || !this.validToken(session.token)
          || !Number.isInteger(session.doctor_id) || !Number.isInteger(session.clinic_id)) {
        localStorage.removeItem(KEY);
        return null;
      }
      return session;
    } catch { return null; }
  }

  private store(session: Session): void {
    try { localStorage.setItem(KEY, JSON.stringify(session)); } catch { /* Memory session still works. */ }
    this.session.set(session);
  }

  register(body: RegisterBody) { return this.api.register(body).pipe(tap((session) => this.store(session))); }
  login(body: LoginBody) { return this.api.login(body).pipe(tap((session) => this.store(session))); }
  join(body: { token: string; doctor_name: string; password: string }) {
    return this.api.join(body).pipe(tap((session) => this.store(session)));
  }

  expireSession(): void {
    const next = this.router.url;
    this.clearSession();
    this.router.navigate(['/login'], { queryParams: { expired: '1', next } });
  }

  private clearSession(): void {
    try { localStorage.removeItem(KEY); } catch { /* Storage may be disabled. */ }
    this.session.set(null);
  }

  logout(): void {
    const token = this.token;
    if (token) this.api.logout(token).subscribe({ error: () => {} });
    this.clearSession();
    try {
      Object.keys(sessionStorage).filter((key) => key.startsWith('perinatal.draft.'))
        .forEach((key) => sessionStorage.removeItem(key));
    } catch { /* Storage may be disabled. */ }
    this.router.navigate(['/login']);
  }

  get token(): string | null { return this.session()?.token ?? null; }
}
