"""cross-store consistency

Revision ID: 20261021150734
Revises: 6644823c3215
Create Date: 2026-10-21 15:07:34.000000

This migration adds version tracking and concurrency control for staged document
re-indexing across PostgreSQL, Qdrant, and Neo4j.

Key changes:
- Add version fields to documents (active_indexing_version, candidate_indexing_version)
- Add version fields to chunks (indexing_version, is_active)
- Add unique constraint preventing concurrent jobs on same document
- Migrate "failed" status to "terminal_failure" for jobs that exhausted retries
- Requeue recoverable failed jobs

See Phase 7.4 design documentation for detailed rationale.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261021150734"
down_revision = "6644823c3215"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply schema changes for cross-store consistency."""
    
    # Detect database dialect for partial index syntax
    # Use context.get_bind() which works in both sync and async Alembic modes
    from alembic import context
    bind = context.get_bind()
    dialect_name = bind.dialect.name
    
    # ========================================================================
    # STEP 1: Add version tracking columns to documents table
    # ========================================================================
    # active_indexing_version: currently serving version (default 1 for existing docs)
    # candidate_indexing_version: version being prepared (NULL when no re-index in progress)
    op.add_column(
        "documents",
        sa.Column(
            "active_indexing_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Currently active indexing version serving retrieval queries"
        )
    )
    op.add_column(
        "documents",
        sa.Column(
            "candidate_indexing_version",
            sa.Integer(),
            nullable=True,
            comment="Version being prepared during re-indexing (NULL when no re-index active)"
        )
    )
    
    # Add index for candidate version lookups (used by activation logic)
    # Partial index to avoid indexing majority of documents with NULL candidate
    # Both SQLite and PostgreSQL support partial indexes with different parameter names
    if dialect_name == "postgresql":
        op.create_index(
            "idx_documents_candidate_version",
            "documents",
            ["candidate_indexing_version"],
            unique=False,
            postgresql_where=sa.text("candidate_indexing_version IS NOT NULL")
        )
    else:  # SQLite
        op.create_index(
            "idx_documents_candidate_version",
            "documents",
            ["candidate_indexing_version"],
            unique=False,
            sqlite_where=sa.text("candidate_indexing_version IS NOT NULL")
        )
    
    # ========================================================================
    # STEP 2: Add version tracking columns to chunks table
    # ========================================================================
    # indexing_version: which document version this chunk belongs to
    # is_active: whether this chunk is currently serving retrieval queries
    op.add_column(
        "chunks",
        sa.Column(
            "indexing_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Document indexing version this chunk belongs to"
        )
    )
    op.add_column(
        "chunks",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",  # Existing chunks are active
            comment="Whether this chunk is currently serving retrieval queries"
        )
    )
    
    # Index for filtering active chunks in retrieval queries
    op.create_index(
        "idx_chunks_is_active",
        "chunks",
        ["is_active"],
        unique=False
    )
    
    # Index for version-based cleanup queries
    op.create_index(
        "idx_chunks_indexing_version",
        "chunks",
        ["indexing_version"],
        unique=False
    )
    
    # Composite index for efficient "active chunks for document" queries
    # Partial index to avoid indexing inactive chunks during re-indexing
    # Note: SQLite stores boolean server_default="true" as string 'true'
    if dialect_name == "postgresql":
        op.create_index(
            "idx_chunks_document_active",
            "chunks",
            ["document_id", "is_active"],
            unique=False,
            postgresql_where=sa.text("is_active = true")
        )
    else:  # SQLite with boolean stored as 'true' string
        op.create_index(
            "idx_chunks_document_active",
            "chunks",
            ["document_id", "is_active"],
            unique=False,
            sqlite_where=sa.text("is_active = 'true' OR is_active = 1")
        )
    
    # ========================================================================
    # STEP 3: Add unique constraint preventing concurrent jobs per document
    # ========================================================================
    # Partial unique index: only one active job (queued/running) per document
    # This prevents race conditions during concurrent re-indexing attempts
    # SQLite and PostgreSQL both support partial indexes with different parameter names
    if dialect_name == "postgresql":
        op.create_index(
            "idx_ingestion_jobs_active_document",
            "ingestion_jobs",
            ["document_id"],
            unique=True,
            postgresql_where=sa.text("status IN ('queued', 'running')")
        )
    else:  # SQLite
        op.create_index(
            "idx_ingestion_jobs_active_document",
            "ingestion_jobs",
            ["document_id"],
            unique=True,
            sqlite_where=sa.text("status IN ('queued', 'running')")
        )
    
    # ========================================================================
    # STEP 4: Migrate job statuses (failed → terminal_failure or requeue)
    # ========================================================================
    # Decision D1: Remove "failed" as terminal status
    # Jobs that exhausted retries → terminal_failure
    # Jobs that can retry → requeue to queued
    
    # Note: Using raw SQL via op.execute for conditional updates
    # SQLAlchemy doesn't support joins in UPDATE, so we use subqueries
    
    # 4a. Mark exhausted jobs as terminal_failure
    op.execute(
        """
        UPDATE ingestion_jobs
        SET status = 'terminal_failure'
        WHERE status = 'failed'
          AND attempts >= max_attempts
        """
    )
    
    # 4b. Requeue recoverable failed jobs, clear error message
    op.execute(
        """
        UPDATE ingestion_jobs
        SET status = 'queued',
            error_message = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE status = 'failed'
          AND attempts < max_attempts
        """
    )
    
    # ========================================================================
    # STEP 5: Add indexing_version column to ingestion_jobs for tracking
    # ========================================================================
    # Track which version this job is creating/updating
    op.add_column(
        "ingestion_jobs",
        sa.Column(
            "indexing_version",
            sa.Integer(),
            nullable=True,
            comment="Document version this job is creating (NULL for legacy jobs)"
        )
    )
    
    # ========================================================================
    # STEP 6: Add checkpoint tracking for durable recovery
    # ========================================================================
    # Track cross-store ingestion progress to enable recovery after failures
    # Checkpoints: persist_chunks → vector_upload → graph_update → activation
    op.add_column(
        "ingestion_jobs",
        sa.Column(
            "checkpoint",
            sa.String(length=64),
            nullable=True,
            comment="Recovery checkpoint: persist_chunks, vector_upload, graph_update, activation"
        )
    )
    
    # Add checkpoint_metadata for storing stage-specific recovery state
    op.add_column(
        "ingestion_jobs",
        sa.Column(
            "checkpoint_metadata",
            sa.JSON(),
            nullable=True,
            server_default="{}",
            comment="Stage-specific recovery state (e.g., last uploaded vector batch)"
        )
    )
    
    # Index for monitoring stuck jobs by checkpoint
    op.create_index(
        "idx_ingestion_jobs_checkpoint",
        "ingestion_jobs",
        ["checkpoint", "status"],
        unique=False
    )


def downgrade() -> None:
    """Revert schema changes."""
    
    # Drop indexes first (foreign key dependencies)
    op.drop_index("idx_ingestion_jobs_checkpoint", table_name="ingestion_jobs")
    op.drop_index("idx_ingestion_jobs_active_document", table_name="ingestion_jobs")
    op.drop_index("idx_chunks_document_active", table_name="chunks")
    op.drop_index("idx_chunks_indexing_version", table_name="chunks")
    op.drop_index("idx_chunks_is_active", table_name="chunks")
    op.drop_index("idx_documents_candidate_version", table_name="documents")
    
    # Drop columns
    op.drop_column("ingestion_jobs", "checkpoint_metadata")
    op.drop_column("ingestion_jobs", "checkpoint")
    op.drop_column("ingestion_jobs", "indexing_version")
    op.drop_column("chunks", "is_active")
    op.drop_column("chunks", "indexing_version")
    op.drop_column("documents", "candidate_indexing_version")
    op.drop_column("documents", "active_indexing_version")
    
    # Revert job status migration (terminal_failure back to failed)
    op.execute(
        """
        UPDATE ingestion_jobs
        SET status = 'failed'
        WHERE status = 'terminal_failure'
        """
    )
