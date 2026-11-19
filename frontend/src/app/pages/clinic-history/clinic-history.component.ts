import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { BirthOutcome, BirthOutcomeInput, OutcomeSummary, PredictResponse } from '../../core/models';

@Component({
  selector: 'app-clinic-history', standalone: true, imports: [CommonModule, FormsModule],
  templateUrl: './clinic-history.component.html', styleUrl: './clinic-history.component.scss',
})
export class ClinicHistoryComponent {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private revision = 0;
  readonly summary = signal<OutcomeSummary | null>(null);
  readonly summaryError = signal('');
  readonly summaryLoading = signal(false);
  readonly countEditing = signal<number | null>(null);
  countDraft: number | null = null;
  readonly survivalBars = computed(() => {
    const s = this.summary()?.survival;
    return s ? [{ label: 'Alive at last follow-up', value: s.alive },
      { label: 'Stillbirth', value: s.stillbirth }, { label: 'Died after live birth', value: s.died },
      { label: 'Outcome not yet known', value: s.pending }] : [];
  });
  readonly weightBars = computed(() => {
    const w = this.summary()?.birth_weight;
    return w ? [{ label: 'Below 2,500 g', value: w.below_2500 },
      { label: '2,500 g or more', value: w.at_least_2500 },
      { label: 'Birth weight not recorded', value: w.unknown }] : [];
  });
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

  babyNumbers(row: PredictResponse): number[] {
    return Array.from({ length: row.baby_count ?? 0 }, (_, i) => i + 1);
  }

  editCount(row: PredictResponse): void {
    this.countEditing.set(row.id); this.countDraft = row.baby_count ?? null;
    this.outcomeError.set('');
  }

  saveCount(row: PredictResponse): void {
    if (this.saving()) return;
    if (!this.countDraft || !Number.isInteger(this.countDraft) || this.countDraft < 1 || this.countDraft > 10) {
      this.outcomeError.set('Choose the confirmed number of babies, from 1 to 10.'); return;
    }
    this.saving.set(true);
    this.api.confirmBabyCount(row.id, this.countDraft, row.baby_count ?? null).subscribe({
      next: updated => {
        const group = updated.pregnancy_id ?? updated.id;
        this.rows.update(rows => rows.map(r => (r.pregnancy_id ?? r.id) === group
          ? { ...r, baby_count: updated.baby_count, multiple: updated.multiple } : r));
        this.saving.set(false); this.countEditing.set(null); this.refreshSummary();
      },
      error: e => {
        this.saving.set(false);
        this.outcomeError.set(e.status === 409 ? 'The baby count changed. Reload the record.'
          : 'Could not save the baby count. It cannot be lower than a baby already followed up.');
      },
    });
  }

  refreshSummary(): void {
    if (this.summaryLoading()) return;
    this.summaryLoading.set(true); this.summaryError.set('');
    this.api.outcomeSummary().subscribe({
      next: value => { this.summary.set(value); this.summaryLoading.set(false); },
      error: () => { this.summaryError.set('Could not load the clinic outcome charts.'); this.summaryLoading.set(false); },
    });
  }

  editOutcome(row: PredictResponse, baby = 1): void {
    if (this.saving() || !this.babyNumbers(row).includes(baby)) return;
    const existing = row.outcomes?.find(o => o.baby_number === baby);
    this.draft = existing ? { ...existing, expected_version: existing.version } : this.emptyOutcome(baby);
    this.editing.set(row.id);
    this.outcomeError.set('');
    this.outcomeSaved.set(null);
  }

  saveOutcome(row: PredictResponse): void {
    if (this.saving()) return;
    if (!this.babyNumbers(row).includes(this.draft.baby_number)) {
      this.outcomeError.set('Choose a baby from the saved baby count.'); return;
    }
    if (!this.draft.source.trim() || !this.draft.observed_on ||
        (this.draft.status !== 'unknown' && !this.draft.birth_date) ||
        (this.draft.status === 'died' && this.draft.death_age_days === null)) {
      this.outcomeError.set('Enter the follow-up date, source and birth details for a known outcome.');
      return;
    }
    this.saving.set(true);
    this.outcomeError.set('');
    const body = { ...this.draft, utc_offset_minutes: -new Date().getTimezoneOffset(), birth_date: this.draft.birth_date || null,
      death_age_days: this.draft.status === 'died' ? this.draft.death_age_days : null };
    this.api.saveOutcome(row.id, body).subscribe({
      next: outcome => {
        this.rows.update(rows => rows.map(r => (r.pregnancy_id ?? r.id) === (row.pregnancy_id ?? row.id) ? { ...r,
          outcomes: [...(r.outcomes ?? []).filter(o => o.baby_number !== outcome.baby_number), outcome]
        } : r));
        this.saving.set(false);
        this.editing.set(null);
        this.outcomeSaved.set(row.id);
        this.revisionRecord.set(null);
        this.refreshSummary();
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

  constructor() { this.load(); this.refreshSummary(); }

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
