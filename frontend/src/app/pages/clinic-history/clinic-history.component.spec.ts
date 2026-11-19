import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ClinicHistoryComponent } from './clinic-history.component';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { BirthOutcome, PredictResponse } from '../../core/models';

describe('ClinicHistoryComponent follow-up', () => {
  let component: ClinicHistoryComponent;
  let api: jasmine.SpyObj<ApiService>;
  const row: PredictResponse = { id: 12, baby_count: 1, pregnancy_id: 12, patient_ref: 'ANC-014', risk: 0.1,
    risk_band: 'unclassified', top_drivers: [], recommendation: 'Review', created_at: '' };
  beforeEach(() => {
    api = jasmine.createSpyObj('ApiService', ['history', 'saveOutcome', 'outcomeHistory', 'outcomeSummary', 'confirmBabyCount']);
    api.history.and.returnValue(of([row]));
    api.outcomeSummary.and.returnValue(of({ pregnancies: 1, babies: 1,
      pregnancies_without_baby_count: 0, survival: { alive: 0, died: 0, stillbirth: 0, pending: 1 },
      birth_weight: { below_2500: 0, at_least_2500: 0, unknown: 1 }, synthetic_excluded: true }));
    TestBed.configureTestingModule({ providers: [
      { provide: ApiService, useValue: api },
      { provide: AuthService, useValue: { session: signal({ clinic_name: 'Clinic' }) } },
    ] });
    component = TestBed.runInInjectionContext(() => new ClinicHistoryComponent());
  });
  it('requires an outcome source and preserves the saved result when follow-up is added', () => {
    component.editOutcome(row);
    component.saveOutcome(row);
    expect(api.saveOutcome).not.toHaveBeenCalled();
    component.draft.source = 'Mother’s report';
    component.draft.notes = 'Referral arranged';
    const outcome: BirthOutcome = { ...component.draft, version: 1, doctor_id: 4, recorded_at: '' };
    api.saveOutcome.and.returnValue(of(outcome));
    component.saveOutcome(row);
    expect(component.rows()[0].outcomes).toEqual([outcome]);
    expect(component.rows()[0].risk).toBe(0.1);
    expect(component.editing()).toBeNull();
  });
  it('keeps entries when another clinician has updated the follow-up', () => {
    component.editOutcome(row);
    component.draft.source = 'Register';
    component.draft.notes = 'Review needed';
    api.saveOutcome.and.returnValue(throwError(() => ({ status: 409 })));
    component.saveOutcome(row);
    expect(component.draft.notes).toBe('Review needed');
    expect(component.outcomeError()).toContain('Another clinician');
    expect(component.editing()).toBe(row.id);
  });
  it('offers exactly the saved baby count and rejects another baby', () => {
    expect(component.babyNumbers({ ...row, baby_count: 3 })).toEqual([1, 2, 3]);
    expect(component.babyNumbers({ ...row, baby_count: null })).toEqual([]);
    component.editOutcome({ ...row, baby_count: 2 }, 3);
    expect(component.editing()).toBeNull();
    component.editOutcome({ ...row, baby_count: 2 }, 2);
    expect(component.draft.baby_number).toBe(2);
  });

  it('shows summary counts from the API independently of loaded history pages', () => {
    expect(component.summary()?.babies).toBe(1);
    component.rows.set([]);
    expect(component.summary()?.babies).toBe(1);
    expect(component.survivalBars().find(b => b.label === 'Outcome not yet known')?.value).toBe(1);
  });

  it('loads the correct baby revision for editing', () => {
    const outcome: BirthOutcome = { baby_number: 2, expected_version: 3, version: 3,
      birth_date: '2026-01-01', observed_on: '2026-01-10', status: 'alive', death_age_days: null,
      birth_weight_grams: 2400, source: 'Register', notes: 'Reviewed', doctor_id: 4, recorded_at: '' };
    component.editOutcome({ ...row, multiple: true, baby_count: 2, outcomes: [outcome] }, 2);
    expect(component.draft.expected_version).toBe(3);
    expect(component.draft.baby_number).toBe(2);
  });
});
