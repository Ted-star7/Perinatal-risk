import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/auth.service';
import { ApiService } from '../../core/api.service';

interface Assessment {
  patientRef: string;
  age: number;
  parity: number;
  intervalMonths: number;
  previousStillbirth: boolean;
  previousLoss: boolean;
  multiple: boolean;
  toldHighBp: boolean;
  ancVisits: number;
}

type RiskRole = 'success' | 'warning' | 'danger';
interface Driver { label: string; weight: number; }
interface Result { risk: number; band: string; role: RiskRole; drivers: Driver[]; recommendation: string; }

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

  readonly clinicName = computed(() => this.auth.session()?.clinic_name ?? '');
  readonly doctorName = computed(() => this.auth.session()?.doctor_name ?? '');

  readonly form = signal<Assessment>({
    patientRef: '', age: 29, parity: 1, intervalMonths: 30,
    previousStillbirth: false, previousLoss: false, multiple: false,
    toldHighBp: false, ancVisits: 3,
  });

  readonly result = computed<Result>(() => this.assess(this.form()));
  readonly saving = signal(false);
  readonly saved = signal(false);

  update<K extends keyof Assessment>(key: K, value: Assessment[K]): void {
    this.form.update((f) => ({ ...f, [key]: value }));
    this.saved.set(false);
  }

  barWidth(): number { return Math.min(100, Math.max(6, this.result().risk * 100 * 7)); }
  maxWeight(): number { return Math.max(...this.result().drivers.map((d) => d.weight), 1); }

  save(): void {
    const f = this.form();
    this.saving.set(true);
    this.api.predict({
      patient_ref: f.patientRef || undefined,
      age: f.age, parity: f.parity, interval_months: f.intervalMonths,
      previous_stillbirth: f.previousStillbirth, previous_loss: f.previousLoss,
      multiple: f.multiple, told_high_bp: f.toldHighBp, anc_visits: f.ancVisits,
    }).subscribe({
      next: () => { this.saving.set(false); this.saved.set(true); },
      error: () => { this.saving.set(false); },
    });
  }

  private assess(f: Assessment): Result {
    const firstPregnancy = f.parity === 0;
    const drivers: Driver[] = [];
    let z = -3.25;
    const add = (c: boolean, w: number, l: string) => { if (c) { z += w; drivers.push({ label: l, weight: w }); } };
    add(f.multiple, 1.4, 'Multiple pregnancy');
    add(f.previousStillbirth, 1.0, 'Previous stillbirth');
    add(f.toldHighBp, 0.9, 'Told high blood pressure');
    add(f.previousLoss, 0.5, 'Previous pregnancy loss');
    add(f.age < 18, 0.4, 'Age under 18');
    add(f.age >= 35, 0.5, 'Age 35 or older');
    add(f.parity >= 5, 0.4, 'Five or more births');
    add(!firstPregnancy && f.intervalMonths > 0 && f.intervalMonths < 24, 0.4, 'Short birth interval');
    add(firstPregnancy, 0.3, 'First pregnancy');
    const risk = 1 / (1 + Math.exp(-z));
    const pct = risk * 100;
    const role: RiskRole = pct < 3 ? 'success' : pct < 8 ? 'warning' : 'danger';
    const band = role === 'success' ? 'low risk' : role === 'warning' ? 'moderate risk' : 'high risk';
    drivers.sort((a, b) => b.weight - a.weight);
    return { risk, band, role, drivers, recommendation: this.recommend(role) };
  }

  private recommend(role: RiskRole): string {
    if (role === 'danger')
      return 'Flag for closer follow-up. Discuss a birth plan and arrange referral to a facility that can manage a high-risk delivery. Check blood pressure and urine at every visit.';
    if (role === 'warning')
      return 'Keep antenatal visits frequent. Check blood pressure and urine, confirm iron is taken, and review again before delivery.';
    return 'Continue routine antenatal care. Keep attending visits so blood pressure, urine and iron can be checked.';
  }
}
