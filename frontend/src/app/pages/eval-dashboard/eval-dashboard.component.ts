import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/api.service';
import { MetricsRow } from '../../core/models';

/** One cohort with its algorithms ranked by PR-AUC (best first). */
interface CohortGroup {
  cohort: string;
  rows: MetricsRow[];
  testEvents: number;
}

const COHORT_ORDER = ['perinatal', 'perinatal_anc', 'lbw'];

/**
 * Backoffice dashboard (dashboard 2 of 2) — for the team and the presentation.
 * Reads the shared /metrics store so every model each person has published shows
 * here, ranked by PR-AUC per cohort. The best model per cohort is marked.
 */
@Component({
  selector: 'app-eval-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './eval-dashboard.component.html',
  styleUrl: './eval-dashboard.component.scss',
})
export class EvalDashboardComponent {
  private api = inject(ApiService);

  readonly loading = signal(true);
  readonly failed = signal(false);
  private readonly rows = signal<MetricsRow[]>([]);

  /** Rows grouped by cohort, each cohort's algorithms sorted best-PR-AUC first. */
  readonly cohorts = computed<CohortGroup[]>(() => {
    const byCohort = new Map<string, MetricsRow[]>();
    for (const r of this.rows()) {
      (byCohort.get(r.cohort) ?? byCohort.set(r.cohort, []).get(r.cohort)!).push(r);
    }
    const order = (c: string) => {
      const i = COHORT_ORDER.indexOf(c);
      return i === -1 ? COHORT_ORDER.length : i;
    };
    return [...byCohort.keys()]
      .sort((a, b) => order(a) - order(b))
      .map((cohort) => {
        const rows = byCohort.get(cohort)!.slice().sort((a, b) => b.pr_auc - a.pr_auc);
        return { cohort, rows, testEvents: rows[0].test_events };
      });
  });

  constructor() {
    this.api.metrics().subscribe({
      next: (r) => {
        this.rows.set(r);
        this.loading.set(false);
      },
      error: () => {
        this.failed.set(true);
        this.loading.set(false);
      },
    });
  }

  /** The winning algorithm in a cohort is the first row (highest PR-AUC). */
  isBest(group: CohortGroup, row: MetricsRow): boolean {
    return group.rows[0] === row;
  }

  prettyAlgo(algorithm: string): string {
    return algorithm.replace(/_/g, ' ');
  }
}
