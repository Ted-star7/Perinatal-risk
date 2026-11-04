import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EvalDashboardComponent } from './eval-dashboard.component';

describe('EvalDashboardComponent', () => {
  let component: EvalDashboardComponent;
  let fixture: ComponentFixture<EvalDashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvalDashboardComponent],
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
});
