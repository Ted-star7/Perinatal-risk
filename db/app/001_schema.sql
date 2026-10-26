-- App DB: read-write. Predictions, recommendations, feedback, audit.
-- SQLAlchemy also creates these on startup; this SQL documents the schema and
-- seeds the Docker Postgres so psql / BI tools see it immediately.

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

-- : clinician verdict on each recommendation.
CREATE TABLE IF NOT EXISTS feedback (
    id              VARCHAR(36) PRIMARY KEY,
    prediction_id   VARCHAR(36) REFERENCES predictions(id),
    created_at      TIMESTAMP DEFAULT now(),
    verdict         VARCHAR(16) CHECK (verdict IN ('good','viable','unusable')),
    note            TEXT
);

CREATE INDEX IF NOT EXISTS ix_rec_pred ON recommendations (prediction_id);
CREATE INDEX IF NOT EXISTS ix_fb_pred ON feedback (prediction_id);
