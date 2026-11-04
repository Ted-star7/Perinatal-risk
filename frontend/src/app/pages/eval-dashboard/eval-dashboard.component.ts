import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

/** One model's headline metrics, as published by the backend /eval endpoint. */
export interface ModelMetrics {
  cohort: string;
  prAuc: number;
  rocAuc: number;
  recallAtFlag: number;   // recall at a fixed flag rate
  beatsChecklist: boolean;
  testEvents: number;
}

/**
 * Backoffice dashboard (dashboard 2 of 2) — for the team and the presentation.
 * Shows how accurate each model is on the held-out test split, calibration, and
 * SHAP. Reads metrics the modeling stage publishes (metrics.json); the numbers
 * below are placeholders until that lands.
 */
@Component({
  selector: 'app-eval-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './eval-dashboard.component.html',
  styleUrl: './eval-dashboard.component.scss',
})
export class EvalDashboardComponent {
  readonly metrics = signal<ModelMetrics[]>([
    { cohort: 'perinatal', prAuc: 0.0, rocAuc: 0.0, recallAtFlag: 0.0, beatsChecklist: false, testEvents: 6189 },
    { cohort: 'perinatal_anc', prAuc: 0.0, rocAuc: 0.0, recallAtFlag: 0.0, beatsChecklist: false, testEvents: 3310 },
    { cohort: 'lbw', prAuc: 0.0, rocAuc: 0.0, recallAtFlag: 0.0, beatsChecklist: false, testEvents: 1849 },
  ]);
}
