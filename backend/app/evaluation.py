"""Install the approved research comparison once, preserving previous submissions."""

import json
from pathlib import Path

from sqlalchemy import text

EVALUATION_ID = "research-2026-11-17-cv"


def install_approved_evaluation(con):
    con.execute(
        text("""CREATE TABLE IF NOT EXISTS approved_model_metrics (
        evaluation_id VARCHAR(80), cohort VARCHAR(32), algorithm VARCHAR(32),
        cv_pr_auc DOUBLE PRECISION, pr_auc DOUBLE PRECISION, payload TEXT NOT NULL,
        PRIMARY KEY(evaluation_id, cohort, algorithm))""")
    )
    con.execute(
        text("""CREATE TABLE IF NOT EXISTS model_metrics_archive (
        evaluation_id VARCHAR(80), cohort VARCHAR(32), algorithm VARCHAR(32), payload TEXT,
        PRIMARY KEY(evaluation_id, cohort, algorithm))""")
    )
    count = con.scalar(
        text("SELECT COUNT(*) FROM approved_model_metrics WHERE evaluation_id=:id"),
        {"id": EVALUATION_ID},
    )
    if count == 9:
        return
    if count:
        raise RuntimeError("The approved comparison is incomplete; refusing to mix runs.")
    path = Path(__file__).resolve().parents[1] / "evaluations/approved.json"
    rows = json.loads(path.read_text())
    assert len(rows) == 9 and len({(r["cohort"], r["algorithm"]) for r in rows}) == 9
    for old in con.execute(text("SELECT * FROM model_metrics")).mappings().all():
        con.execute(
            text("""INSERT INTO model_metrics_archive
            VALUES (:id,:cohort,:algorithm,:payload)
            ON CONFLICT(evaluation_id,cohort,algorithm) DO NOTHING"""),
            {
                "id": EVALUATION_ID,
                "cohort": old["cohort"],
                "algorithm": old["algorithm"],
                "payload": json.dumps(dict(old), default=str),
            },
        )
    con.execute(text("UPDATE model_metrics SET is_best=FALSE"))
    for row in rows:
        con.execute(
            text("""INSERT INTO approved_model_metrics VALUES
            (:evaluation_id,:cohort,:algorithm,:cv_pr_auc,:pr_auc,:payload)"""),
            dict(row, payload=json.dumps(row)),
        )
        con.execute(
            text("""INSERT INTO model_metrics
            (cohort,algorithm,pr_auc,roc_auc,recall_at_flag,beats_checklist,is_best,test_events)
            VALUES (:cohort,:algorithm,:pr_auc,:roc_auc,:recall_at_flag,
                    :beats_checklist,:is_best,:test_events)
            ON CONFLICT(cohort,algorithm) DO UPDATE SET
            pr_auc=excluded.pr_auc,roc_auc=excluded.roc_auc,recall_at_flag=excluded.recall_at_flag,
            beats_checklist=excluded.beats_checklist,is_best=excluded.is_best,
            test_events=excluded.test_events,updated_at=CURRENT_TIMESTAMP"""),
            row,
        )


def approved_evaluation(db):
    return [
        json.loads(row[0])
        for row in db.execute(
            text("SELECT payload FROM approved_model_metrics WHERE evaluation_id=:id"),
            {"id": EVALUATION_ID},
        )
    ]
