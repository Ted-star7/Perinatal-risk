
import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/api.service';

/** Model evaluation metrics displayed in simple, understandable language. */
export interface ModelMetrics {
  cvPrAuc?: number;
  casesCaught?: number;
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

export interface CohortPerformanceGroup {
  cohort: string;
  title: string;
  models: ModelMetrics[];
  topModels: ModelMetrics[];
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
  readonly cohorts = ['perinatal', 'lbw', 'perinatal_anc'];
  readonly cohortGroups = computed<CohortPerformanceGroup[]>(() =>
    this.cohorts.map((cohort) => {
      const models = this.rows(cohort);
      return { cohort, title: this.cohortLabel(cohort), models, topModels: models.slice(0, 2) };
    }).filter((group) => group.models.length > 0),
  );
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
      next: (records) => {
        const mappedRecords: ModelMetrics[] = records.map((record) => ({
          cohort: record.cohort,
          cvPrAuc: record.cv_pr_auc,
          casesCaught: record.cases_caught,
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
      error: () => {
        this.error.set('Unable to load model results. Please try again.');
        this.loading.set(false);
      },
    });
  }

  rows(cohort: string): ModelMetrics[] {
    return this.metrics().filter((row) => row.cohort === cohort)
      .sort((a, b) => (b.cvPrAuc ?? -1) - (a.cvPrAuc ?? -1) || a.algorithm.localeCompare(b.algorithm));
  }

  cohortLabel(cohort: string): string {
    const labels: Record<string, string> = {
      perinatal: 'Primary outcome: risk of death around birth (perinatal death)',
      lbw: 'Secondary outcome: babies born weighing less than 2.5 kg (low birth weight)',
      perinatal_anc: 'Perinatal ANC: pregnancy check-up cohort (research comparison)',
    };
    return labels[cohort] ?? cohort;
  }

  algorithmLabel(algorithm: string): string {
    const labels: Record<string, string> = {
      logistic_regression: 'Statistical risk model (logistic regression)',
      gradient_boosting: 'Decision trees refined in stages (gradient boosting)',
      random_forest: 'Combined decision trees (random forest)',
      checklist: 'Pregnancy checklist (baseline)',
    };
    return labels[algorithm] ?? algorithm;
  }
}
