-- Clean data DB: cleaned DHS cohorts (the feature store).
-- READ-ONLY to the app. Written only by ml/src/load_dhs.py (custodian).
-- One table per cohort; columns follow contracts/feature_spec.yaml.

CREATE SCHEMA IF NOT EXISTS clean;

-- Example: headline cohort. load_dhs.py creates/populates these in stage 2.
CREATE TABLE IF NOT EXISTS clean.perinatal_full (
    id                     BIGSERIAL PRIMARY KEY,
    country                TEXT NOT NULL,
    cluster_id             INTEGER,          -- v001, for grouped CV
    sample_weight          DOUBLE PRECISION, -- v005 / 1e6
    mother_age             INTEGER,
    parity                 INTEGER,
    prev_stillbirth        BOOLEAN,
    birth_interval_months  INTEGER,
    multiple_pregnancy     BOOLEAN,
    education              TEXT,
    wealth_quintile        TEXT,
    residence              TEXT,
    region                 TEXT,
    perinatal_death        BOOLEAN           -- outcome
);

CREATE INDEX IF NOT EXISTS ix_pf_country ON clean.perinatal_full (country);
CREATE INDEX IF NOT EXISTS ix_pf_cluster ON clean.perinatal_full (cluster_id);
