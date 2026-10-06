from pathlib import Path
import re
from sqlalchemy import inspect, text

from app.db import engine
from app.models import Document, ExtractedField, Job, LineItem, User, ValidationIssue


def test_models_match_migrated_database_columns() -> None:
    inspector = inspect(engine)
    expected_models = [User, Document, Job, ExtractedField, LineItem, ValidationIssue]

    for model in expected_models:
        table_name = model.__tablename__
        db_columns = {column["name"] for column in inspector.get_columns(table_name)}
        model_columns = {column.name for column in model.__table__.columns}
        assert db_columns == model_columns, f"Columns mismatch for table {table_name}"


def test_required_tables_and_indexes_exist() -> None:
    inspector = inspect(engine)

    assert {
        "users",
        "documents",
        "jobs",
        "extracted_fields",
        "line_items",
        "validation_issues",
    }.issubset(set(inspector.get_table_names()))

    document_indexes = {index["name"] for index in inspector.get_indexes("documents")}
    job_indexes = {index["name"] for index in inspector.get_indexes("jobs")}

    assert "uq_documents_user_hash_primary" in document_indexes
    assert "idx_documents_user_status" in document_indexes
    assert "idx_jobs_document" in job_indexes


def test_partial_unique_index_definition() -> None:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename = 'documents' AND indexname = 'uq_documents_user_hash_primary'"
            )
        ).fetchone()

        assert result is not None, "uq_documents_user_hash_primary index not found in pg_indexes"
        indexdef = result[1]
        assert "UNIQUE INDEX" in indexdef
        assert "user_id" in indexdef
        assert "file_hash" in indexdef
        assert "status <> 'duplicate'" in indexdef or "(status <> 'duplicate'::text)" in indexdef


def test_schema_sql_contract_alignment() -> None:
    schema_path = Path("/contracts/schema.sql")
    if not schema_path.exists():
        # Fallback to relative path if not running inside root container
        schema_path = Path(__file__).resolve().parents[2] / "contracts" / "schema.sql"

    if schema_path.exists():
        content = schema_path.read_text(encoding="utf-8")
        tables_in_sql = set(re.findall(r"CREATE\s+TABLE\s+(\w+)", content, re.IGNORECASE))
        expected_tables = {
            "users",
            "documents",
            "jobs",
            "extracted_fields",
            "line_items",
            "validation_issues",
        }
        assert tables_in_sql == expected_tables, f"Tables mismatch in schema.sql: {tables_in_sql}"

