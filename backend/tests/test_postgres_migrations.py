"""Exercise migrations against a disposable PostgreSQL schema in CI."""

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text


@unittest.skipUnless(os.getenv("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for PostgreSQL checks.")
class PostgresMigrationTests(unittest.TestCase):
    def test_existing_rows_survive_concurrent_idempotent_migration(self):
        from app import database

        url = os.environ["TEST_POSTGRES_URL"]
        admin = create_engine(url)
        schema = "audit_" + uuid4().hex
        with admin.begin() as con:
            con.execute(text(f"CREATE SCHEMA {schema}"))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
        try:
            with engine.begin() as con:
                con.execute(
                    text("""CREATE TABLE predictions (
                    id INTEGER PRIMARY KEY, clinic_id INTEGER, risk DOUBLE PRECISION)""")
                )
                con.execute(
                    text("INSERT INTO predictions(id, clinic_id, risk) VALUES (1, 1, 0.03)")
                )
            with patch.object(database, "engine", engine):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    list(pool.map(lambda _: database.init_db(), range(2)))
            with engine.connect() as con:
                self.assertEqual(
                    con.execute(text("SELECT risk FROM predictions WHERE id = 1")).scalar(), 0.03
                )
                self.assertEqual(
                    con.execute(text("SELECT MAX(version) FROM schema_migrations")).scalar(), 6
                )
                prediction_columns = {c["name"] for c in inspect(con).get_columns("predictions")}
                self.assertTrue({"baby_count", "pregnancy_id"} <= prediction_columns)
                self.assertEqual(
                    con.scalar(text("SELECT pregnancy_id FROM predictions WHERE id=1")), 1
                )
                columns = {column["name"] for column in inspect(con).get_columns("doctors")}
                self.assertTrue({"token_version", "is_active", "is_owner"} <= columns)
        finally:
            engine.dispose()
            with admin.begin() as con:
                con.execute(text(f"DROP SCHEMA {schema} CASCADE"))
            admin.dispose()
