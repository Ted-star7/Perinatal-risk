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
  readonly isLoggedIn = computed(() => this.session() !== null);

  private restore(): Session | null {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  }

  private store(s: Session): void {
    localStorage.setItem(KEY, JSON.stringify(s));
    this.session.set(s);
  }

  register(body: RegisterBody) {
    return this.api.register(body).pipe(tap((s) => this.store(s)));
  }

  login(body: LoginBody) {
    return this.api.login(body).pipe(tap((s) => this.store(s)));
  }

  logout(): void {
    localStorage.removeItem(KEY);
    this.session.set(null);
    this.router.navigate(['/login']);
  }

  get token(): string | null {
    return this.session()?.token ?? null;
  }
}
