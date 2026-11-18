import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { BirthOutcome, BirthOutcomeInput, PredictResponse } from '../../core/models';

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
  readonly editing = signal<number | null>(null);
  readonly saving = signal(false);
  readonly outcomeError = signal('');
  readonly outcomeSaved = signal<number | null>(null);
  readonly revisions = signal<BirthOutcome[]>([]);
  readonly revisionRecord = signal<number | null>(null);
  readonly historyLoading = signal(false);
  draft: BirthOutcomeInput = this.emptyOutcome(1);
  search = '';

  private emptyOutcome(baby: number): BirthOutcomeInput {
    const now = new Date();
    const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    return { baby_number: baby, expected_version: 0, birth_date: null,
      observed_on: localDate, status: 'unknown', death_age_days: null,
      birth_weight_grams: null, source: '', notes: '' };
  }

  editOutcome(row: PredictResponse, baby = 1): void {
    if (this.saving()) return;
    const existing = row.outcomes?.find(o => o.baby_number === baby);
    this.draft = existing ? { ...existing, expected_version: existing.version } : this.emptyOutcome(baby);
    this.editing.set(row.id);
    this.outcomeError.set('');
    this.outcomeSaved.set(null);
  }

  saveOutcome(row: PredictResponse): void {
    if (this.saving()) return;
    if (!this.draft.source.trim() || !this.draft.observed_on ||
        (this.draft.status !== 'unknown' && !this.draft.birth_date) ||
        (this.draft.status === 'died' && this.draft.death_age_days === null)) {
      this.outcomeError.set('Enter the follow-up date, source and birth details for a known outcome.');
      return;
    }
    this.saving.set(true);
    this.outcomeError.set('');
    const body = { ...this.draft, birth_date: this.draft.birth_date || null,
      death_age_days: this.draft.status === 'died' ? this.draft.death_age_days : null };
    this.api.saveOutcome(row.id, body).subscribe({
      next: outcome => {
        this.rows.update(rows => rows.map(r => r.id === row.id ? { ...r,
          outcomes: [...(r.outcomes ?? []).filter(o => o.baby_number !== outcome.baby_number), outcome]
        } : r));
        this.saving.set(false);
        this.editing.set(null);
        this.outcomeSaved.set(row.id);
        this.revisionRecord.set(null);
      },
      error: error => {
        this.saving.set(false);
        this.outcomeError.set(error.status === 409
          ? 'Another clinician updated this record. Reload the records and reopen follow-up.'
          : error.status === 422 ? 'Check the dates, weight and age at death. Future or inconsistent dates cannot be saved.'
          : 'Follow-up was not confirmed as saved. Your entries are still here; try again.');
      },
    });
  }

  viewRevisions(id: number): void {
    if (this.historyLoading()) return;
    this.historyLoading.set(true);
    this.api.outcomeHistory(id).subscribe({
      next: rows => { this.revisions.set(rows); this.revisionRecord.set(id); this.historyLoading.set(false); },
      error: () => { this.error.set('Could not load follow-up history. Try again.'); this.historyLoading.set(false); },
    });
  }

  outcomeLabel(status: BirthOutcomeInput['status']): string {
    return { unknown: 'Not yet known', alive: 'Alive at follow-up', stillbirth: 'Stillbirth',
      died: 'Died after live birth' }[status];
  }

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
