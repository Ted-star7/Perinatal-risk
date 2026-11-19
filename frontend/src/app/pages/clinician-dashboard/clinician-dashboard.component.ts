import { Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../core/auth.service';
import { ApiService } from '../../core/api.service';
import { AssessmentResult, PatientLookup, PredictRequest } from '../../core/models';

interface Assessment {
  patientRef: string;
  age: number | null;
  firstPregnancy: boolean | null;
  parity: number | null;
  previousStillbirth: boolean | null;
  previousLoss: boolean | null;
  multiple: boolean | null;
  babyCount: number | null;
  birthSpacing: number | null;
  pregnancyId: number | null;
  education: PredictRequest['education'];
}

const EMPTY_FORM: Assessment = {
  patientRef: '', age: null, firstPregnancy: null, parity: null,
  previousStillbirth: null, previousLoss: null,
  multiple: null, babyCount: null, birthSpacing: null, pregnancyId: null, education: null,
};

@Component({
  selector: 'app-clinician-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './clinician-dashboard.component.html',
  styleUrl: './clinician-dashboard.component.scss',
})
export class ClinicianDashboardComponent {
  private auth = inject(AuthService);
  private api = inject(ApiService);
  private revision = 0;
  private destroyRef = inject(DestroyRef);
  private lookupTimer: ReturnType<typeof setTimeout> | undefined;
  private lookupRevision = 0;
  readonly patientLookup = signal<PatientLookup | null>(null);
  readonly lookupLoading = signal(false);
  readonly lookupError = signal('');
  readonly patientChoice = signal<'new' | 'continue' | null>(null);
  private requestId = crypto.randomUUID();

  readonly clinicName = computed(() => this.auth.session()?.clinic_name ?? '');
  readonly doctorName = computed(() => this.auth.session()?.doctor_name ?? '');
  readonly form = signal<Assessment>({ ...EMPTY_FORM });
  readonly submitted = signal(false);
  readonly keepDraft = signal(false);
  readonly result = signal<AssessmentResult | null>(null);
  readonly calculating = signal(false);
  readonly saving = signal(false);
  readonly saved = signal(false);
  readonly error = signal('');
  readonly busy = computed(() => this.calculating() || this.saving());

  readonly errors = computed<Record<string, string>>(() => {
    const f = this.form();
    const errors: Record<string, string> = {};
    const validateNumber = (key: keyof Assessment, min: number, max: number, required: boolean) => {
      const value = f[key];
      if (value === null && !required) return;
      if (typeof value !== 'number' || !Number.isInteger(value) || value < min || value > max) {
        errors[key] = `Enter a whole number from ${min} to ${max}.`;
      }
    };
    if (!f.patientRef.trim()) errors['patientRef'] = 'Enter the patient’s ANC card or clinic reference.';
    else if (f.patientRef.trim().length > 60) errors['patientRef'] = 'Use no more than 60 characters.';
    if (this.lookupError()) errors['patientRef'] = 'Retry patient lookup before continuing.';
    if (this.lookupLoading()) errors['patientRef'] = 'Checking this patient reference…';
    if (this.patientLookup()?.found && !this.patientChoice()) {
      errors['patientRef'] = 'Choose whether this is the same pregnancy or a new pregnancy.';
    }
    if (f.multiple === true) validateNumber('babyCount', 2, 10, true);
    validateNumber('birthSpacing', 0, 480, false);
    validateNumber('age', 11, 55, true);
    validateNumber('parity', 0, 16, true);
    for (const key of ['firstPregnancy', 'previousStillbirth', 'previousLoss', 'multiple'] as const) {
      if (f[key] === null) errors[key] = 'Choose Yes or No.';
    }
    return errors;
  });

  constructor() {
    this.destroyRef.onDestroy(() => { clearTimeout(this.lookupTimer); this.lookupRevision++; });
    this.restoreDraft();
    if (this.form().patientRef.trim()) this.findPatient();
  }

  findPatient(): void {
    clearTimeout(this.lookupTimer);
    const reference = this.form().patientRef.trim();
    const revision = ++this.lookupRevision;
    this.patientLookup.set(null);
    this.lookupError.set('');
    if (!reference || reference.length > 60) { this.lookupLoading.set(false); return; }
    this.lookupLoading.set(true);
    this.api.patientLookup(reference).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => {
        if (revision !== this.lookupRevision || reference !== this.form().patientRef.trim()) return;
        this.patientLookup.set(result);
        this.lookupLoading.set(false);
      },
      error: () => {
        if (revision !== this.lookupRevision) return;
        this.lookupLoading.set(false);
        this.lookupError.set('Could not check earlier records. Retry before linking a previous pregnancy.');
      },
    });
  }

  usePreviousPregnancy(): void {
    const record = this.patientLookup();
    if (!record?.found || !record.latest || !record.inputs || this.busy()) return;
    const f = record.inputs;
    this.revision++;
    this.requestId = crypto.randomUUID();
    this.form.set({ patientRef: record.latest.patient_ref ?? this.form().patientRef,
      age: f.age_at_start ?? null, firstPregnancy: f.first_pregnancy ?? null,
      parity: f.parity ?? null, previousStillbirth: f.previous_stillbirth ?? null,
      previousLoss: f.previous_loss ?? null,
      multiple: record.latest.multiple ?? f.multiple ?? null,
      babyCount: record.latest.baby_count ?? null,
      birthSpacing: f.birth_spacing_months ?? null,
      pregnancyId: record.latest.pregnancy_id ?? record.latest.id,
      education: f.education ?? null });
    this.patientChoice.set('continue');
    this.result.set(null); this.saved.set(false); this.submitted.set(false);
    this.persistDraft();
  }

  newPregnancy(): void {
    if (this.busy()) return;
    this.revision++;
    this.requestId = crypto.randomUUID();
    this.form.set({ ...EMPTY_FORM, patientRef: this.form().patientRef,
      education: this.patientLookup()?.inputs?.education ?? null });
    this.patientChoice.set('new');
    this.result.set(null); this.saved.set(false); this.submitted.set(false);
    this.persistDraft();
  }

  private draftKey(): string | null {
    const session = this.auth.session();
    return session?.doctor_id && session?.clinic_id
      ? `perinatal.draft.${session.clinic_id}.${session.doctor_id}` : null;
  }

  toggleDraft(enabled: boolean): void {
    this.keepDraft.set(enabled);
    if (enabled) this.persistDraft(); else this.clearDraft();
  }

  private persistDraft(): void {
    const key = this.draftKey();
    if (!key || !this.keepDraft()) return;
    try {
      sessionStorage.setItem(key, JSON.stringify({
        version: 3, form: this.form(), requestId: this.requestId, result: this.result(), updatedAt: Date.now(),
      }));
    } catch { this.error.set('This browser could not keep the draft. Keep this tab open while working.'); }
  }

  private restoreDraft(): void {
    const key = this.draftKey();
    if (!key) return;
    try {
      const raw = sessionStorage.getItem(key);
      if (!raw) return;
      const draft = JSON.parse(raw);
      if (draft.version !== 3) {
        sessionStorage.removeItem(key);
        this.error.set('The assessment questions have changed. Enter the details again, including age when the pregnancy began.');
        return;
      }
      if (!draft.form || typeof draft.requestId !== 'string'
          || Date.now() - draft.updatedAt > 2 * 60 * 60 * 1000) {
        sessionStorage.removeItem(key);
        return;
      }
      this.form.set({ ...EMPTY_FORM, ...draft.form });
      this.patientChoice.set(draft.form.pregnancyId ? 'continue' : 'new');
      this.requestId = draft.requestId;
      this.result.set(draft.result ?? null);
      this.keepDraft.set(true);
    } catch { this.clearDraft(); }
  }

  private clearDraft(): void {
    const key = this.draftKey();
    try { if (key) sessionStorage.removeItem(key); } catch { /* Storage may be disabled. */ }
  }

  update<K extends keyof Assessment>(key: K, value: Assessment[K]): void {
    this.revision++;
    this.requestId = crypto.randomUUID();
    this.form.update((form) => {
      const next = key === 'patientRef'
        ? { ...EMPTY_FORM, patientRef: value as string } : { ...form, [key]: value };
      if (key === 'multiple') next.babyCount = value === false ? 1 : null;
      if (key === 'firstPregnancy') {
        next.birthSpacing = null;
        next.parity = value === true ? 0 : null;
        next.previousStillbirth = value === true ? false : null;
        next.previousLoss = value === true ? false : null;
      }
      return next;
    });
    this.result.set(null);
    this.saved.set(false);
    this.error.set('');
    if (key === 'patientRef') {
      clearTimeout(this.lookupTimer);
      this.lookupRevision++;
      this.patientLookup.set(null);
      this.patientChoice.set(null);
      this.lookupError.set('');
      this.lookupLoading.set(!!this.form().patientRef.trim());
      this.lookupTimer = setTimeout(() => this.findPatient(), 450);
    }
    this.persistDraft();
  }

  startAnother(): void {
    if (this.busy()) return;
    clearTimeout(this.lookupTimer); this.lookupRevision++;
    this.patientLookup.set(null); this.lookupLoading.set(false); this.lookupError.set('');
    this.patientChoice.set(null);
    this.clearDraft();
    this.keepDraft.set(false);
    this.revision++;
    this.requestId = crypto.randomUUID();
    this.form.set({ ...EMPTY_FORM });
    this.result.set(null);
    this.submitted.set(false);
    this.saved.set(false);
    this.error.set('');
  }

  private request(): PredictRequest {
    const f = this.form();
    return {
      request_id: this.requestId,
      assessment_token: this.result()?.assessment_token ?? undefined,
      patient_ref: f.patientRef.trim(),
      age_at_start: f.age!, parity: f.parity!, first_pregnancy: f.firstPregnancy!,
      previous_stillbirth: f.previousStillbirth!, previous_loss: f.previousLoss!,
      multiple: f.multiple!, baby_count: f.multiple ? f.babyCount! : 1,
      pregnancy_id: f.pregnancyId, birth_spacing_months: f.birthSpacing,
      education: f.education,
    };
  }

  assess(): void {
    this.submitted.set(true);
    if (this.busy() || Object.keys(this.errors()).length) return;
    const revision = this.revision;
    this.calculating.set(true);
    this.error.set('');
    this.api.assess(this.request()).subscribe({
      next: (result) => {
        this.calculating.set(false);
        if (revision === this.revision) { this.result.set(result); this.persistDraft(); }
      },
      error: (error: HttpErrorResponse) => {
        this.calculating.set(false);
        if (revision === this.revision) this.error.set(this.errorMessage(error));
      },
    });
  }

  save(): void {
    if (this.busy() || this.saved() || !this.result() || Object.keys(this.errors()).length) return;
    const revision = this.revision;
    this.saving.set(true);
    this.error.set('');
    this.api.predict(this.request()).subscribe({
      next: (saved) => {
        this.saving.set(false);
        if (revision === this.revision) {
          this.result.set(saved.assessment ?? null);
          this.saved.set(true);
          this.clearDraft();
          this.keepDraft.set(false);
        }
      },
      error: (error: HttpErrorResponse) => {
        this.saving.set(false);
        if (revision === this.revision) this.error.set(this.errorMessage(error));
      },
    });
  }

  private errorMessage(error: HttpErrorResponse): string {
    if (error.status === 409) {
      this.result.set(null);
      return 'This assessment needs refreshing. Select Assess pregnancy again before saving.';
    }
    if (error.status === 401 || error.status === 403) return 'Your session has ended. Sign in again to continue.';
    if (error.status === 503) return 'The prediction service is unavailable. Your entries are still here. Try again or contact the project team.';
    if (error.status === 422) return 'Some entries need checking. Review the pregnancy details and try again.';
    return 'We could not confirm the request. Check your connection. Your entries are still here.';
  }
}
