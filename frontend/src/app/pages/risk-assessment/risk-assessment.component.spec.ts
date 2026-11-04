import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RiskAssessmentComponent } from './risk-assessment.component';

describe('RiskAssessmentComponent', () => {
  let component: RiskAssessmentComponent;
  let fixture: ComponentFixture<RiskAssessmentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RiskAssessmentComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(RiskAssessmentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('creates', () => {
    expect(component).toBeTruthy();
  });

  it('starts at a low-risk band for a routine pregnancy', () => {
    expect(component.result().role).toBe('success');
  });

  it('raises the risk and band when high-risk factors are set', () => {
    const baseline = component.result().risk;
    component.update('multiple', true);
    component.update('previousStillbirth', true);
    component.update('toldHighBp', true);

    const result = component.result();
    expect(result.risk).toBeGreaterThan(baseline);
    expect(result.role).toBe('danger');
    expect(result.drivers.map((d) => d.label)).toContain('Multiple pregnancy');
  });

  it('lists drivers strongest-first', () => {
    component.update('previousLoss', true); // weight 0.5
    component.update('multiple', true); // weight 1.4
    const weights = component.result().drivers.map((d) => d.weight);
    expect(weights).toEqual([...weights].sort((a, b) => b - a));
  });
});
