import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AppComponent } from './app.component';
import { AuthService } from './core/auth.service';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: {
          isLoggedIn: signal(true), session: signal({ clinic_name: 'Test clinic' }),
        } },
      ],
    }).compileComponents();
  });

  it('offers assessment and history navigation for a signed-in clinician', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('nav a[href="/triage"]')?.textContent).toContain('Assessment');
    expect(element.querySelector('a[href="/history"]')?.textContent).toContain('Clinic records');
    expect(element.querySelector('a[href="/performance"]')).toBeNull();
  });
});
