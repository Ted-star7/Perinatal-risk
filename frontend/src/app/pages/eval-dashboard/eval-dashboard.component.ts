
import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, ModelMetricResponse } from '../../core/api.service';

/** Model evaluation metrics displayed in simple, understandable language. */
export interface ModelMetrics {
  cohort: string;
  algorithm: string;
  prAuc: number;
  rocAuc: number;
  recallAtFlag: number;
  beatsChecklist: boolean;
  isBest: boolean;
  testEvents: number;
  updatedAt: string;
}

@Component({
  selector: 'app-eval-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './eval-dashboard.component.html',
  styleUrl: './eval-dashboard.component.scss',
})
export class EvalDashboardComponent implements OnInit {
  readonly metrics = signal<ModelMetrics[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadMetrics();
  }

  /** Retrieve the latest shared model evaluation results. */
  loadMetrics(): void {
    this.loading.set(true);
    this.error.set('');

    this.api.metrics().subscribe({
      next: (records: ModelMetricResponse[]) => {
        const mappedRecords: ModelMetrics[] = records.map((record) => ({
          cohort: record.cohort,
          algorithm: record.algorithm,
          prAuc: record.pr_auc,
          rocAuc: record.roc_auc,
          recallAtFlag: record.recall_at_flag,
          beatsChecklist: record.beats_checklist,
          isBest: record.is_best,
          testEvents: record.test_events,
          updatedAt: record.updated_at,
        }));

        this.metrics.set(mappedRecords);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Could not load model metrics:', err);
        this.error.set(
          'Unable to load model performance results. Please try again.'
        );
        this.loading.set(false);
      },
    });
  }

  /** Convert technical cohort identifiers into familiar descriptions. */
 cohortLabel(cohort: string): string {
  const labels: Record<string, string> = {
    lbw: 'Babies born weighing less than 2.5 kg',
    perinatal: 'Risk of death around birth',
    perinatal_anc: 'Risk of death around birth (with pregnancy check-up information)',
  };

  return labels[cohort] ?? cohort;
}

  /** Convert technical algorithm identifiers into readable names. */
  algorithmLabel(algorithm: string): string {
    const labels: Record<string, string> = {
      gradient_boosting: 'Gradient Boosting',
      random_forest: 'Random Forest',
    };

    return labels[algorithm] ?? algorithm;
  }
}
