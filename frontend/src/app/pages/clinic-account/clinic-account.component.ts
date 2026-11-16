import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { PasswordToggleComponent } from '../../shared/password-toggle/password-toggle.component';
import { AuthService } from '../../core/auth.service';
import { API_BASE, ApiService } from '../../core/api.service';

interface Colleague { id: number; name: string; email: string; is_active: boolean; is_owner: boolean; }

@Component({
  selector: 'app-clinic-account', standalone: true, imports: [CommonModule, FormsModule, RouterLink, PasswordToggleComponent],
  templateUrl: './clinic-account.component.html', styleUrl: './clinic-account.component.scss',
})
export class ClinicAccountComponent {
  readonly auth = inject(AuthService);
  private api = inject(ApiService);
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  readonly mode = this.route.snapshot.data['mode'] as 'team' | 'password' | 'join';
  readonly busy = signal(false);
  readonly error = signal('');
  readonly message = signal('');
  readonly link = signal('');
  readonly colleagues = signal<Colleague[]>([]);
  email = '';
  name = '';
  currentPassword = '';
  newPassword = '';

  constructor() { if (this.mode === 'team') this.loadTeam(); }

  private loadTeam(): void {
    this.http.get<Colleague[]>(`${API_BASE}/clinics/team`).subscribe({
      next: (rows) => this.colleagues.set(rows),
      error: () => this.error.set('Only the clinic owner can manage the team.'),
    });
  }

  submit(): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    this.message.set('');
    if (this.mode === 'team') {
      this.api.invite(this.email).subscribe({
        next: (invitation) => {
          this.link.set(`${location.origin}/join?token=${encodeURIComponent(invitation.token)}`);
          this.busy.set(false);
        }, error: (error) => this.fail(error),
      });
    } else if (this.mode === 'password') {
      this.api.changePassword(this.currentPassword, this.newPassword).subscribe({
        next: () => { this.busy.set(false); this.auth.logout(); },
        error: (error) => this.fail(error),
      });
    } else {
      const token = this.route.snapshot.queryParamMap.get('token') ?? '';
      this.auth.join({ token, doctor_name: this.name, password: this.newPassword }).subscribe({
        next: () => this.router.navigate(['/triage']), error: (error) => this.fail(error),
      });
    }
  }

  deactivate(colleague: Colleague): void {
    this.http.post(`${API_BASE}/clinics/team/${colleague.id}/deactivate`, {}).subscribe({
      next: () => this.loadTeam(), error: (error) => this.fail(error),
    });
  }

  private fail(error: { error?: { detail?: unknown } }): void {
    this.busy.set(false);
    const detail = error.error?.detail;
    this.error.set(typeof detail === 'string' ? detail : 'Check the details and try again.');
  }
}
