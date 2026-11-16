import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { PredictResponse } from '../../core/models';

@Component({
  selector: 'app-clinic-history', standalone: true, imports: [CommonModule, FormsModule],
  templateUrl: './clinic-history.component.html', styleUrl: './clinic-history.component.scss',
})
export class ClinicHistoryComponent {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private revision = 0;
  readonly clinicName = computed(() => this.auth.session()?.clinic_name ?? '');
  readonly rows = signal<PredictResponse[]>([]);
  readonly loading = signal(false);
  readonly more = signal(false);
  readonly error = signal('');
  search = '';
  constructor() { this.load(); }

  load(append = false): void {
    if (this.loading()) return;
    const revision = ++this.revision;
    this.loading.set(true);
    this.error.set('');
    const rows = this.rows();
    const before = append && rows.length ? rows[rows.length - 1].id : undefined;
    this.api.history(this.search, before).subscribe({
      next: (page) => {
        if (revision !== this.revision) return;
        this.rows.set(append ? [...rows, ...page] : page);
        this.more.set(page.length === 25);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('We could not load the clinic records. Check your connection and try again.');
      },
    });
  }
}
