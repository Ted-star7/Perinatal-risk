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

  /** Current risk-band filter: 'all' | 'high' | 'moderate' | 'low'. */
  readonly filter = signal<'all' | 'high' | 'moderate' | 'low'>('all');
  readonly filteredRows = computed(() => {
    const f = this.filter();
    return f === 'all' ? this.rows() : this.rows().filter((r) => r.risk_band === f);
  });

  readonly total = computed(() => this.rows().length);
  readonly highCount = computed(() => this.rows().filter((r) => r.risk_band === 'high').length);

  setFilter(f: 'all' | 'high' | 'moderate' | 'low'): void {
    this.filter.set(f);
  }

  constructor() {
    this.api.history().subscribe({
      next: (rows) => { this.rows.set(rows); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }
}
