import { HttpClient } from '@angular/common/http';
import { Type, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { AppComponent } from '../app.component';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { AssessmentResult } from '../core/models';
import { ClinicAccountComponent } from './clinic-account/clinic-account.component';
import { ClinicHistoryComponent } from './clinic-history/clinic-history.component';
import { ClinicianDashboardComponent } from './clinician-dashboard/clinician-dashboard.component';
import { EvalDashboardComponent } from './eval-dashboard/eval-dashboard.component';
import { LoginComponent } from './login/login.component';
import { RegisterComponent } from './register/register.component';

const assessment: AssessmentResult = {
  perinatal: {
    status: 'available', label: 'Risk around birth', description: 'Stillbirth or death in the first seven days after birth.',
    score: 0.035, model_id: 'test-primary', message: 'Research estimate', calibrated: true,
  },
  lbw: {
    status: 'available', label: 'Low birth weight', description: 'A baby weighing less than 2.5 kg at birth.',
    score: 0.075, model_id: 'test-secondary', message: 'Research estimate', calibrated: true,
  },
  baseline: { flagged: true, factors: ['Mother is 35 years or older'], unknown_factors: [], summary: 'Review this pregnancy.' },
  recommendation: 'Review the checklist factors and agree on a follow-up plan.', notes: [],
};

const pages: Type<unknown>[] = [
  AppComponent, LoginComponent, RegisterComponent, ClinicianDashboardComponent,
  ClinicHistoryComponent, ClinicAccountComponent, EvalDashboardComponent,
];

async function frameFor(element: HTMLElement, width: number): Promise<HTMLIFrameElement> {
  const frame = document.createElement('iframe');
  frame.style.cssText = `position:fixed;left:0;top:0;width:${width}px;height:900px;border:0;visibility:hidden`;
  const styles = [...document.head.querySelectorAll('style, link[rel="stylesheet"]')]
    .map((node) => node.outerHTML).join('\n');
  const loaded = new Promise<void>((resolve) => { frame.onload = () => resolve(); });
  frame.srcdoc = `<!doctype html><html><head>${styles}</head><body>${element.outerHTML}</body></html>`;
  document.body.append(frame);
  await loaded;
  await frame.contentDocument!.fonts.ready;
  return frame;
}

describe('Clinician portal layouts', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: pages,
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: {
          snapshot: { data: { mode: 'password' }, queryParamMap: convertToParamMap({}) },
        } },
        { provide: AuthService, useValue: {
          isLoggedIn: signal(true),
          session: signal({ doctor_id: 1, clinic_id: 1, doctor_name: 'Test clinician', clinic_name: 'Test clinic' }),
        } },
        { provide: ApiService, useValue: { history: () => of([]), metrics: () => of([]), releases: () => of([]) } },
        { provide: HttpClient, useValue: { get: () => of([]) } },
      ],
    }).compileComponents();
  });

  for (const page of pages) {
    it(`${page.name} fits mobile, tablet and desktop widths`, async () => {
      const fixture = TestBed.createComponent(page);
      const component = fixture.componentInstance;
      if (component instanceof ClinicianDashboardComponent) {
        component.update('firstPregnancy', false);
        component.result.set(assessment);
      }
      if (component instanceof ClinicHistoryComponent) {
        component.rows.set([{
          id: 1, patient_ref: 'ANC-' + 'X'.repeat(56), created_at: '2026-11-15T10:00:00Z',
          risk: 0.035, risk_band: 'unclassified', top_drivers: [], recommendation: 'Review the assessment.',
          assessment,
        }]);
      }
      fixture.detectChanges();
      await fixture.whenStable();
      for (const width of [320, 390, 600, 768, 1024, 1440]) {
        const frame = await frameFor(fixture.nativeElement, width);
        try {
          const root = frame.contentDocument!.documentElement;
          expect(root.scrollWidth).withContext(`${page.name} at ${width}px`).toBeLessThanOrEqual(root.clientWidth + 1);
          for (const field of frame.contentDocument!.querySelectorAll('input, select, button')) {
            const rect = field.getBoundingClientRect();
            if (rect.width > 0) {
              expect(rect.left).withContext(`Field left edge at ${width}px`).toBeGreaterThanOrEqual(0);
              expect(rect.right).withContext(`Field right edge at ${width}px`).toBeLessThanOrEqual(root.clientWidth + 1);
            }
          }
        } finally {
          frame.remove();
        }
      }
      fixture.destroy();
    });
  }

  it('keeps the phone input aligned with the facility type', async () => {
    const fixture = TestBed.createComponent(RegisterComponent);
    fixture.detectChanges();
    const frame = await frameFor(fixture.nativeElement, 1440);
    try {
      const doc = frame.contentDocument!;
      const phone = doc.querySelector<HTMLInputElement>('input[name="phone"]')!;
      const facility = doc.querySelector<HTMLSelectElement>('select[name="type"]')!;
      expect(Math.abs(phone.getBoundingClientRect().top - facility.getBoundingClientRect().top)).toBeLessThan(2);
    } finally {
      frame.remove();
    }
  });

  for (const page of [LoginComponent, RegisterComponent, ClinicAccountComponent] as Type<unknown>[]) {
    it(`${page.name} shows and hides passwords without submitting`, () => {
      const fixture = TestBed.createComponent(page);
      fixture.detectChanges();
      const element = fixture.nativeElement as HTMLElement;
      for (const field of element.querySelectorAll('.password-field')) {
        const input = field.querySelector('input')!;
        const toggle = field.querySelector('button')!;
        input.value = 'clinic88';
        expect(toggle.type).toBe('button');
        expect(input.type).toBe('password');
        toggle.click();
        fixture.detectChanges();
        expect(input.type).toBe('text');
        expect(toggle.getAttribute('aria-label')).toBe('Hide password');
        toggle.click();
        fixture.detectChanges();
        expect(input.type).toBe('password');
        expect(input.value).toBe('clinic88');
      }
    });
  }
});
