import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EvalDashboardComponent } from './eval-dashboard.component';
import { of, throwError } from 'rxjs';
import { ApiService, ModelMetricResponse } from '../../core/api.service';

const records: ModelMetricResponse[] = ['perinatal', 'perinatal_anc', 'lbw'].map((cohort) => ({
  cv_pr_auc: 0.1, cohort, algorithm: 'random_forest', pr_auc: 0.1, roc_auc: 0.6,
  recall_at_flag: 0.5, beats_checklist: true, is_best: true,
  test_events: 100, updated_at: '2026-11-15T00:00:00',
}));

describe('EvalDashboardComponent', () => {
  let component: EvalDashboardComponent;
  let fixture: ComponentFixture<EvalDashboardComponent>;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('ApiService', ['metrics', 'releases']);
    api.metrics.and.returnValue(of(records));
    api.releases.and.returnValue(of([]));
    await TestBed.configureTestingModule({
      imports: [EvalDashboardComponent],
      providers: [{ provide: ApiService, useValue: api }],
    }).compileComponents();

    fixture = TestBed.createComponent(EvalDashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('creates', () => {
    expect(component).toBeTruthy();
  });

  it('has one metrics row per cohort', () => {
    expect(component.metrics().length).toBe(3);
  });

  it('orders cohorts and selects by CV rather than test AP', () => {
    expect(component.cohortGroups().map(g => g.cohort)).toEqual(['perinatal', 'lbw', 'perinatal_anc']);
    component.metrics.set([
      { cohort: 'lbw', algorithm: 'random_forest', cvPrAuc: 0.19, prAuc: 0.14,
        rocAuc: 0.6, recallAtFlag: 0.5, beatsChecklist: true, isBest: true, testEvents: 100, updatedAt: '' },
      { cohort: 'lbw', algorithm: 'gradient_boosting', cvPrAuc: 0.18, prAuc: 0.17,
        rocAuc: 0.6, recallAtFlag: 0.5, beatsChecklist: true, isBest: false, testEvents: 100, updatedAt: '' },
    ]);
    fixture.detectChanges();
    expect(component.rows('lbw')[0].algorithm).toBe('random_forest');
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('.source-switch')).toBeNull();
    expect(element.querySelector('.release-report')).toBeNull();
    expect(api.releases).not.toHaveBeenCalled();
  });

  it('lets the user retry a failed metrics request', () => {
    api.metrics.and.returnValue(throwError(() => new Error('Offline')));
    component.loadMetrics();
    fixture.detectChanges();
    const retry = fixture.nativeElement.querySelector('.error button') as HTMLButtonElement;
    expect(retry).not.toBeNull();
    api.metrics.and.returnValue(of(records));
    retry.click();
    fixture.detectChanges();
    expect(component.error()).toBe('');
    expect(component.metrics().length).toBe(3);
  });

  it('shows the empty state without empty comparison tables', () => {
    api.metrics.and.returnValue(of([]));
    component.loadMetrics();
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('table')).toBeNull();
    expect(element.querySelector('[role="status"]')?.textContent).toContain('No model results are available yet.');
  });

});
