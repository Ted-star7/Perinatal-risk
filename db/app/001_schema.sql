-- App DB: read-write. Holds live app use (predictions, recommendations,
-- feedback) and the training results the eval dashboard reads (model_metrics,
-- feature_importance). Created on container start; also documents the schema.

CREATE TABLE IF NOT EXISTS predictions (
    id              VARCHAR(36) PRIMARY KEY,
    created_at      TIMESTAMP DEFAULT now(),
    model_version   VARCHAR(32),
    inputs          JSONB,
    risk            DOUBLE PRECISION,
    risk_band       VARCHAR(16),
    checklist_flag  BOOLEAN,
    top_drivers     JSONB
);

CREATE TABLE IF NOT EXISTS recommendations (
    id              VARCHAR(36) PRIMARY KEY,
    prediction_id   VARCHAR(36) REFERENCES predictions(id),
    created_at      TIMESTAMP DEFAULT now(),
    text            TEXT,
    llm_model       VARCHAR(64)
);

-- Clinician verdict on each recommendation.
CREATE TABLE IF NOT EXISTS feedback (
    id              VARCHAR(36) PRIMARY KEY,
    prediction_id   VARCHAR(36) REFERENCES predictions(id),
    created_at      TIMESTAMP DEFAULT now(),
    verdict         VARCHAR(16) CHECK (verdict IN ('good','viable','unusable')),
    note            TEXT
);

-- One row per (cohort, algorithm). Each modeling notebook upserts its result;
-- the eval dashboard reads this. Unique key lets us replace on re-run.
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

-- Top SHAP drivers for the winning model of each cohort (drivers chart).
CREATE TABLE IF NOT EXISTS feature_importance (
    cohort          VARCHAR(32),
    feature         VARCHAR(64),
    importance      DOUBLE PRECISION,
    PRIMARY KEY (cohort, feature)
);

CREATE INDEX IF NOT EXISTS ix_rec_pred ON recommendations (prediction_id);
CREATE INDEX IF NOT EXISTS ix_fb_pred ON feedback (prediction_id);
