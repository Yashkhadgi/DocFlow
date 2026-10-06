"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";

        CREATE TABLE users (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          email         TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          full_name     TEXT,
          created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE documents (
          id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          filename         TEXT NOT NULL,
          mime_type        TEXT NOT NULL,
          size_bytes       BIGINT NOT NULL,
          file_hash        CHAR(64) NOT NULL,
          storage_key      TEXT NOT NULL,
          status           TEXT NOT NULL CHECK (status IN
                           ('queued','processing','needs_review','approved','failed','duplicate')),
          auto_approved    BOOLEAN NOT NULL DEFAULT FALSE,
          duplicate_of_id  UUID REFERENCES documents(id),
          duplicate_reason TEXT,
          error_message    TEXT,
          approved_at      TIMESTAMPTZ,
          created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX uq_documents_user_hash_primary
          ON documents (user_id, file_hash) WHERE status <> 'duplicate';
        CREATE INDEX idx_documents_user_status ON documents (user_id, status, created_at DESC);

        CREATE TABLE jobs (
          id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id    UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          celery_task_id TEXT,
          status         TEXT NOT NULL CHECK (status IN ('queued','processing','succeeded','failed')),
          attempts       INT NOT NULL DEFAULT 0,
          max_attempts   INT NOT NULL DEFAULT 3,
          last_error     TEXT,
          started_at     TIMESTAMPTZ,
          finished_at    TIMESTAMPTZ,
          created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_jobs_document ON jobs (document_id);

        CREATE TABLE extracted_fields (
          id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id    UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          field_name     TEXT NOT NULL,
          value          TEXT,
          confidence     NUMERIC(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
          needs_review   BOOLEAN NOT NULL DEFAULT FALSE,
          reviewed_value TEXT,
          bbox           JSONB,
          UNIQUE (document_id, field_name)
        );

        CREATE TABLE line_items (
          id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          position     INT NOT NULL,
          description  TEXT,
          quantity     NUMERIC(14,3),
          rate         NUMERIC(14,2),
          amount       NUMERIC(14,2),
          confidence   NUMERIC(4,3)
        );

        CREATE TABLE validation_issues (
          id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          rule         TEXT NOT NULL,
          severity     TEXT NOT NULL CHECK (severity IN ('error','warning')),
          field_name   TEXT,
          message      TEXT NOT NULL
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS validation_issues;
        DROP TABLE IF EXISTS line_items;
        DROP TABLE IF EXISTS extracted_fields;
        DROP TABLE IF EXISTS jobs;
        DROP TABLE IF EXISTS documents;
        DROP TABLE IF EXISTS users;
        """
    )
