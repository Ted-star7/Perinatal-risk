import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { PredictResponse } from '../../core/models';

@Component({
  selector: 'app-clinic-history',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './clinic-history.component.html',
  styleUrl: './clinic-history.component.scss',
})
export class ClinicHistoryComponent {
  private api = inject(ApiService);
  private auth = inject(AuthService);

  readonly clinicName = computed(() => this.auth.session()?.clinic_name ?? '');
  readonly rows = signal<PredictResponse[]>([]);
  readonly loading = signal(true);

  readonly total = computed(() => this.rows().length);
  readonly highCount = computed(() => this.rows().filter((r) => r.risk_band === 'high').length);

  constructor() {
    this.api.history().subscribe({
      next: (rows) => { this.rows.set(rows); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }
}
