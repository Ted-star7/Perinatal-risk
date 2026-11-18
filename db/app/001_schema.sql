-- App DB. The backend (SQLAlchemy) owns clinics, doctors, predictions and birth_outcomes and
-- creates them on startup. This file seeds only the tables the modeling side
-- writes and the eval dashboard reads.

-- One row per (cohort, algorithm); each modeling notebook upserts its result.
CREATE TABLE IF NOT EXISTS model_metrics (
    cohort          VARCHAR(32),
    algorithm       VARCHAR(32),
    pr_auc          DOUBLE PRECISION,
    roc_auc         DOUBLE PRECISION,
    recall_at_flag  DOUBLE PRECISION,
    beats_checklist BOOLEAN,
    is_best         BOOLEAN DEFAULT FALSE,
    test_events     INTEGER,
    updated_at      TIMESTAMP DEFAULT now(),
    PRIMARY KEY (cohort, algorithm)
);

-- Top drivers for the winning model of each cohort (drivers chart).
CREATE TABLE IF NOT EXISTS feature_importance (
    cohort          VARCHAR(32),
    feature         VARCHAR(64),
    importance      DOUBLE PRECISION,
    PRIMARY KEY (cohort, feature)
);
