import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { PasswordToggleComponent } from '../../shared/password-toggle/password-toggle.component';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, PasswordToggleComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  readonly route = inject(ActivatedRoute);

  email = '';
  password = '';
  readonly error = signal('');
  readonly busy = signal(false);

  submit(): void {
    if (this.busy() || !this.email.trim() || !this.password) return;
    this.error.set('');
    this.busy.set(true);
    this.auth.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        const next = this.route.snapshot.queryParamMap.get('next');
        this.router.navigateByUrl(next?.startsWith('/') && !next.startsWith('//') ? next : '/triage');
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(e?.error?.detail ?? 'Could not sign in. Try again.');
      },
    });
  }
}
