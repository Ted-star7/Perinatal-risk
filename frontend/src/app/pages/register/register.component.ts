import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { PasswordToggleComponent } from '../../shared/password-toggle/password-toggle.component';
import { AuthService } from '../../core/auth.service';
import { RegisterBody } from '../../core/models';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, PasswordToggleComponent],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss',
})
export class RegisterComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  readonly form: RegisterBody = {
    clinic_name: '',
    type: 'Health centre',
    county: '',
    country: '',
    phone: '',
    doctor_name: '',
    email: '',
    password: '',
  };
  readonly types = ['Hospital', 'Health centre', 'Private clinic'];

  readonly error = signal('');
  readonly busy = signal(false);

  submit(): void {
    if (this.busy()) return;
    this.error.set('');
    this.busy.set(true);
    this.auth.register(this.form).subscribe({
      next: () => this.router.navigate(['/assess']),
      error: (e) => {
        this.busy.set(false);
        this.error.set(e?.error?.detail ?? 'Could not register. Try again.');
      },
    });
  }
}
