import { fakeAsync, tick, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { of, Subject, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { ClinicianDashboardComponent } from './clinician-dashboard.component';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { AssessmentResult } from '../../core/models';

const assessment: AssessmentResult = {
  perinatal: { status: 'available', label: 'Perinatal outcome', description: 'Perinatal outcome',
    score: 0.12, model_id: 'primary:test', message: 'Research score' },
  lbw: { status: 'available', label: 'Low birth weight', description: 'Birth weight under 2.5 kg',
    score: 0.24, model_id: 'secondary:test', message: 'Research score' },
  baseline: { flagged: false, factors: [], unknown_factors: [], summary: 'No factors found' },
  recommendation: 'Review the assessment.', notes: [],
};

describe('ClinicianDashboardComponent', () => {
  let component: ClinicianDashboardComponent;
  let api: jasmine.SpyObj<ApiService>;

  function completeForm(): void {
    component.update('patientRef', 'ANC-014');
    component.findPatient();
    component.update('age', 29);
    component.update('firstPregnancy', true);
    component.update('multiple', false);
  }

  beforeEach(async () => {
    api = jasmine.createSpyObj('ApiService', ['assess', 'predict', 'patientLookup']);
    api.assess.and.returnValue(of(assessment));
    api.patientLookup.and.returnValue(of({ found: false, assessment_count: 0, latest: null, inputs: null }));
    await TestBed.configureTestingModule({
      imports: [ClinicianDashboardComponent],
      providers: [
        { provide: ApiService, useValue: api },
        { provide: AuthService, useValue: { session: signal({ clinic_name: 'Clinic', doctor_name: 'Doctor' }) } },
      ],
    }).compileComponents();
    component = TestBed.createComponent(ClinicianDashboardComponent).componentInstance;
  });

  it('requires answers before requesting a result', () => {
    component.assess();
    expect(api.assess).not.toHaveBeenCalled();
    expect(component.result()).toBeNull();
  });

  it('rejects a blank patient reference and sends a trimmed reference', () => {
    completeForm();
    component.update('patientRef', '   ');
    component.assess();
    expect(api.assess).not.toHaveBeenCalled();
    component.update('patientRef', ' ANC-014 ');
    component.findPatient();
    component.update('age', 29);
    component.update('firstPregnancy', true);
    component.update('multiple', false);
    component.assess();
    expect(api.assess.calls.mostRecent().args[0].patient_ref).toBe('ANC-014');
  });

  it('checks the exact reference after typing and clears another patient’s details', fakeAsync(() => {
    completeForm();
    api.patientLookup.calls.reset();
    component.update('patientRef', 'OTHER-014');
    expect(component.form().age).toBeNull();
    expect(component.form().pregnancyId).toBeNull();
    tick(449);
    expect(api.patientLookup).not.toHaveBeenCalled();
    tick(1);
    expect(api.patientLookup).toHaveBeenCalledOnceWith('OTHER-014');
    expect(component.lookupLoading()).toBeFalse();
  }));

  it('loads a returning pregnancy and keeps new-pregnancy details separate', () => {
    api.patientLookup.and.returnValue(of({ found: true, assessment_count: 2,
      latest: { id: 11, pregnancy_id: 10, baby_count: 3, multiple: true,
        patient_ref: 'ANC-014', risk: 0.1, risk_band: 'unclassified', top_drivers: [],
        recommendation: '', created_at: '' },
      inputs: { age_at_start: 29, first_pregnancy: false, parity: 1,
        previous_loss: false, previous_stillbirth: false, education: 'Primary', birth_spacing_months: 18 } }));
    component.update('patientRef', 'ANC-014');
    component.findPatient();
    component.assess();
    expect(api.assess).not.toHaveBeenCalled();
    component.usePreviousPregnancy();
    expect(component.form().babyCount).toBe(3);
    expect(component.form().pregnancyId).toBe(10);
    expect(component.form().birthSpacing).toBe(18);
    component.assess();
    expect(api.assess.calls.mostRecent().args[0].baby_count).toBe(3);
    expect(api.assess.calls.mostRecent().args[0].pregnancy_id).toBe(10);
    component.newPregnancy();
    expect(component.form().age).toBeNull();
    expect(component.form().babyCount).toBeNull();
    expect(component.form().pregnancyId).toBeNull();
    expect(component.form().education).toBe('Primary');
  });

  it('ignores a patient lookup response for a superseded reference', () => {
    const response = new Subject<any>();
    api.patientLookup.and.returnValue(response);
    component.update('patientRef', 'OLD'); component.findPatient();
    component.update('patientRef', 'NEW');
    response.next({ found: true, assessment_count: 1, latest: null, inputs: null });
    expect(component.patientLookup()).toBeNull();
  });

  it('shows the API result for both outcomes', () => {
    completeForm();
    component.assess();
    expect(component.result()).toEqual(assessment);
    expect(api.assess.calls.mostRecent().args[0].first_pregnancy).toBeTrue();
    expect(api.assess.calls.mostRecent().args[0].age_at_start).toBe(29);
    expect(api.assess.calls.mostRecent().args[0].anc_visits).toBeUndefined();
  });

  it('shows the inputs reported by each fitted model and identifies the record reference', () => {
    const fixture = TestBed.createComponent(ClinicianDashboardComponent);
    fixture.componentInstance.result.set({
      ...assessment,
      perinatal: { ...assessment.perinatal, used_inputs: ['Mother’s age', 'Twins or more babies'] },
      lbw: { ...assessment.lbw, used_inputs: ['Highest education level', 'First pregnancy'] },
    });
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    const details = element.querySelector('.follow-up details')!;
    expect(details.textContent).toContain('Information used for risk around birth');
    expect(details.textContent).toContain('Twins or more babies');
    expect(details.textContent).toContain('Information used for low birth weight');
    expect(details.textContent).toContain('Highest education level');
    expect(element.querySelector('#patient-reference-help')?.textContent).toContain('recordkeeping');
  });

  it('clears a previous result when inputs change', () => {
    completeForm();
    component.assess();
    component.update('multiple', true);
    expect(component.result()).toBeNull();
    expect(component.saved()).toBeFalse();
  });

  it('starts another assessment with empty patient details', () => {
    completeForm();
    component.assess();
    component.startAnother();
    expect(component.form().age).toBeNull();
    expect(component.form().firstPregnancy).toBeNull();
    expect(component.result()).toBeNull();
    expect(component.submitted()).toBeFalse();
  });

  it('discards a response for superseded inputs', () => {
    const response = new Subject<AssessmentResult>();
    api.assess.and.returnValue(response);
    completeForm();
    component.assess();
    component.update('age', 30);
    response.next(assessment);
    expect(component.result()).toBeNull();
  });

  it('keeps entries and explains a connection failure', () => {
    completeForm();
    api.assess.and.returnValue(throwError(() => new HttpErrorResponse({ status: 0 })));
    component.assess();
    expect(component.error()).toContain('connection');
    expect(component.form().age).toBe(29);
    expect(component.calculating()).toBeFalse();
  });

  it('reuses the request identity on a save retry and blocks another save after success', () => {
    completeForm();
    component.assess();
    api.predict.and.returnValue(throwError(() => new HttpErrorResponse({ status: 0 })));
    component.save();
    const requestId = api.predict.calls.mostRecent().args[0].request_id;
    api.predict.and.returnValue(of({
      id: 1, risk: 0.12, risk_band: 'unclassified', top_drivers: [],
      recommendation: assessment.recommendation, created_at: '', assessment,
    }));
    component.save();
    expect(api.predict.calls.mostRecent().args[0].request_id).toBe(requestId);
    expect(component.saved()).toBeTrue();
    component.save();
    expect(api.predict).toHaveBeenCalledTimes(2);
  });
});
