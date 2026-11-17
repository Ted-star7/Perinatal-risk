import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EvalDashboardComponent } from './eval-dashboard.component';
import { of, Subject, throwError } from 'rxjs';
import { ApiService, ModelMetricResponse, ModelRelease } from '../../core/api.service';

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

  it('orders both sources as primary outcome, secondary outcome and then ANC', () => {
    component.releases.set(['lbw', 'perinatal_anc', 'perinatal'].map((cohort) => ({
      cohort, available: true,
    })));
    expect(component.cohortGroups().map((group) => group.cohort))
      .toEqual(['perinatal', 'lbw', 'perinatal_anc']);
    expect(component.orderedReleases().map((model) => model.cohort))
      .toEqual(['perinatal', 'lbw', 'perinatal_anc']);
  });

  it('keeps submitted rankings separate from a release with the same algorithm name', () => {
    const base = records[2];
    api.metrics.and.returnValue(of([
      { ...base, algorithm: 'random_forest', cv_pr_auc: 0.19, pr_auc: 0.14 },
      { ...base, algorithm: 'gradient_boosting', cv_pr_auc: 0.18, pr_auc: 0.17, is_best: false },
      { ...base, algorithm: 'logistic_regression', cv_pr_auc: 0.17, pr_auc: 0.13, is_best: false },
    ]));
    api.releases.and.returnValue(of([{
      cohort: 'lbw', algorithm: 'random_forest', available: true, serving: true,
      model_id: 'selected:release-hash', prediction_context: 'antenatal_history_v1',
      evaluation: {
        selection: 'Highest grouped training CV average precision.',
        test: { pr_auc: 0.144, roc_auc: 0.652, mean_score: 0.08, event_rate: 0.07, brier_score: 0.06 },
      },
    }]));
    component.loadMetrics();
    fixture.detectChanges();
    expect(component.cohortGroups()[0].topModels.map((row) => row.algorithm))
      .toEqual(['random_forest', 'gradient_boosting']);
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('tbody tr.selected')).toBeNull();
    expect(element.querySelector('.calibration')).toBeNull();
    expect(element.querySelector('.release-report')).toBeNull();

    const switcher = element.querySelectorAll<HTMLButtonElement>('.source-switch button');
    switcher[1].click();
    fixture.detectChanges();
    const release = element.querySelector('.release-report')!;
    expect(element.querySelector('table')).toBeNull();
    expect(release.querySelector('.release-pr')?.textContent?.trim()).toBe('0.144');
    expect(release.textContent).toContain('random forest');
    expect(release.textContent).toContain('selected:release-hash');
    expect(release.textContent).toContain('Highest grouped training CV average precision.');
    expect(release.textContent).not.toContain('0.140');
    expect(switcher[1].getAttribute('aria-pressed')).toBe('true');
  });

  it('waits for model information before showing the completed comparison', () => {
    const releases = new Subject<ModelRelease[]>();
    api.releases.and.returnValue(releases);
    component.loadMetrics();
    expect(component.loading()).toBeTrue();
    releases.next([{ cohort: 'lbw', available: true, algorithm: 'gradient_boosting' }]);
    releases.complete();
    expect(component.loading()).toBeFalse();
    expect(component.releases()[0]?.algorithm).toBe('gradient_boosting');
  });

  it('keeps evaluation results available when model information cannot be checked', () => {
    api.releases.and.returnValue(throwError(() => new Error('Unavailable')));
    component.loadMetrics();
    expect(component.loading()).toBeFalse();
    expect(component.error()).toBe('');
    expect(component.metrics().length).toBe(3);
    expect(component.releases()).toEqual([]);
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

  it('shows API releases even if the submissions request fails', () => {
    api.metrics.and.returnValue(throwError(() => new Error('Offline')));
    api.releases.and.returnValue(of([{
      cohort: 'lbw', algorithm: 'random_forest', available: true, serving: true,
      evaluation: { test: { pr_auc: 0.144, mean_score: 0.08, event_rate: 0.07, brier_score: 0.06 } },
    }]));
    component.loadMetrics();
    component.view.set('releases');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.release-pr')?.textContent?.trim()).toBe('0.144');
    expect(fixture.nativeElement.querySelector('[role="alert"]')).toBeNull();
  });
});
