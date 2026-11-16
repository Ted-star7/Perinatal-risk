import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, ModelMetricResponse } from '../../core/api.service';

export interface ModelMetrics {
  cohort: string;
  algorithm: string;
  prAuc: number;
  rocAuc: number;
  recallAtFlag: number;
  beatsChecklist: boolean;
  testEvents: number;
  updatedAt: string;
}

export interface CohortPerformanceGroup {
  cohort: string;
  title: string;
  description: string;
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
  readonly loading = signal(true);
  readonly error = signal('');

  private readonly cohortOrder = ['lbw', 'perinatal', 'perinatal_anc'];

  readonly cohortGroups = computed<CohortPerformanceGroup[]>(() => {
    const records = this.metrics();
    const groups: CohortPerformanceGroup[] = [];

    for (const cohort of this.cohortOrder) {
      const models = records
        .filter((record) => record.cohort === cohort)
        .sort((a, b) => b.prAuc - a.prAuc);

      if (models.length === 0) {
        continue;
      }

      groups.push({
        cohort,
        title: this.cohortTitle(cohort),
        description: this.cohortDescription(cohort),
        models,
        topModels: models.slice(0, 2),
      });
    }

    return groups;
  });

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadMetrics();
  }

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

  cohortTitle(cohort: string): string {
    const labels: Record<string, string> = {
      lbw: 'Low birth weight prediction',
      perinatal: 'Perinatal death prediction',
      perinatal_anc: 'ANC-enhanced perinatal death prediction',
    };

    return labels[cohort] ?? cohort;
  }

  cohortDescription(cohort: string): string {
    const descriptions: Record<string, string> = {
      lbw: 'Identifying babies born weighing less than 2.5 kg.',
      perinatal: 'Identifying babies at risk of death around birth.',
      perinatal_anc:
        'Perinatal death prediction incorporating antenatal care information.',
    };

    return descriptions[cohort] ?? '';
  }

  algorithmLabel(algorithm: string): string {
    const labels: Record<string, string> = {
      gradient_boosting: 'Gradient Boosting',
      random_forest: 'Random Forest',
      logistic_regression: 'Logistic Regression',
    };

    return labels[algorithm] ?? algorithm;
  }
}
