import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

/** The pregnancy-time details a clinician enters for one assessment. */
export interface Assessment {
  age: number;
  parity: number;            // previous live births
  intervalMonths: number;    // months since last birth (0 = not applicable)
  previousStillbirth: boolean;
  previousLoss: boolean;
  multiple: boolean;         // multiple pregnancy
  toldHighBp: boolean;
  ancVisits: number;
  residence: 'Urban' | 'Rural';
  education: 'No education' | 'Primary' | 'Secondary' | 'Higher';
}

type RiskRole = 'success' | 'warning' | 'danger';

interface Driver {
  label: string;
  weight: number;
}

interface Result {
  risk: number;              // 0..1
  band: string;              // 'low risk' | 'moderate risk' | 'high risk'
  role: RiskRole;            // drives the colour
  drivers: Driver[];
  recommendation: string;
}

@Component({
  selector: 'app-risk-assessment',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './risk-assessment.component.html',
  styleUrl: './risk-assessment.component.scss',
})
export class RiskAssessmentComponent {
  /** The form state. A signal so the result recomputes whenever it changes. */
  readonly form = signal<Assessment>({
    age: 29,
    parity: 1,
    intervalMonths: 30,
    previousStillbirth: false,
    previousLoss: false,
    multiple: false,
    toldHighBp: false,
    ancVisits: 3,
    residence: 'Urban',
    education: 'Secondary',
  });

  /** Derived risk, recomputed automatically when the form changes. */
  readonly result = computed<Result>(() => this.assess(this.form()));

  /** Update one field (called from the template on every change). */
  update<K extends keyof Assessment>(key: K, value: Assessment[K]): void {
    this.form.update((f) => ({ ...f, [key]: value }));
  }

  /** Progress-bar width for the risk card (clamped so it's always visible). */
  barWidth(): number {
    return Math.min(100, Math.max(6, this.result().risk * 100 * 7));
  }

  /** Largest driver weight, used to scale the driver bars to full width. */
  maxWeight(): number {
    return Math.max(...this.result().drivers.map((d) => d.weight), 1);
  }

  /**
   * Demonstration scoring. This mirrors the drivers found in the EDA and is a
   * placeholder for the real model served by the backend — the backend returns
   * the score and SHAP drivers, and this component just renders them.
   */
  private assess(f: Assessment): Result {
    const firstPregnancy = f.parity === 0;
    const drivers: Driver[] = [];
    let z = -3.25; // log-odds baseline ~3.7%

    const add = (cond: boolean, weight: number, label: string) => {
      if (cond) {
        z += weight;
        drivers.push({ label, weight });
      }
    };

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
    switch (role) {
      case 'danger':
        return 'Flag for closer follow-up. Discuss a birth plan and arrange referral to a facility that can manage a high-risk delivery. Check blood pressure and urine at every visit.';
      case 'warning':
        return 'Keep antenatal visits frequent. Check blood pressure and urine, confirm iron is taken, and review again before delivery.';
      default:
        return 'Continue routine antenatal care. Keep attending visits so blood pressure, urine and iron can be checked.';
    }
  }
}
