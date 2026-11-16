import { Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from './core/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  readonly auth = inject(AuthService);
  readonly initials = computed(() => (this.auth.session()?.doctor_name ?? 'Clinician')
    .replace(/^Dr\.?\s*/i, '').split(/\s+/).slice(0, 2).map((part) => part[0]).join(''));
}
