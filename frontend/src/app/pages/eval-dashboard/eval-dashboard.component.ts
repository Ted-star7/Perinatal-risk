
import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { catchError, forkJoin, of } from 'rxjs';
import { ApiService, ModelRelease } from '../../core/api.service';

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
  readonly releases = signal<ModelRelease[]>([]);
  readonly view = signal<'submissions' | 'releases'>('submissions');
  readonly releaseError = signal('');
  readonly cohorts = ['perinatal', 'lbw', 'perinatal_anc'];
  readonly orderedReleases = computed(() =>
    this.cohorts.flatMap((cohort) => this.releases().filter((model) => model.cohort === cohort)),
  );
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
    this.releaseError.set('');

    forkJoin({
      records: this.api.metrics().pipe(catchError(() => {
        this.error.set('Unable to load submitted model results. Please try again.');
        return of([]);
      })),
      releases: this.api.releases().pipe(catchError(() => {
        this.releaseError.set('Unable to check the API model releases. Please try again.');
        return of([]);
      })),
    }).subscribe({
      next: ({ records, releases }) => {
        this.releases.set(releases);
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
    });
  }

  rows(cohort: string): ModelMetrics[] {
    return this.metrics().filter((row) => row.cohort === cohort)
      .sort((a, b) => b.prAuc - a.prAuc || a.algorithm.localeCompare(b.algorithm));
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
