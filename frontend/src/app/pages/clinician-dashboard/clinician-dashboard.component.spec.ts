import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ClinicianDashboardComponent } from './clinician-dashboard.component';

describe('ClinicianDashboardComponent', () => {
  let component: ClinicianDashboardComponent;
  let fixture: ComponentFixture<ClinicianDashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ClinicianDashboardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ClinicianDashboardComponent);
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
