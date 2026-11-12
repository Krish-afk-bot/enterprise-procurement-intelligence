"""worker leases for ingestion jobs

Revision ID: 20261105120000
Revises: 20261022104000
Create Date: 2026-11-05 12:00:00.000000

A running job is owned by a worker only while its lease is valid. The worker
renews the lease from a heartbeat task; crash recovery requeues a job only once
the lease has expired, so a long ingestion is never taken from a healthy worker.

Both columns are nullable: existing running jobs keep ``lease_expires_at`` NULL
and are recovered by the legacy start-time rule until they are next claimed.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261105120000"
down_revision = "20261022104000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ingestion_jobs") as batch_op:
        batch_op.add_column(sa.Column("lease_token", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index("ix_ingestion_jobs_lease_token", ["lease_token"])
        batch_op.create_index("ix_ingestion_jobs_lease_expires_at", ["lease_expires_at"])


def downgrade() -> None:
    with op.batch_alter_table("ingestion_jobs") as batch_op:
        batch_op.drop_index("ix_ingestion_jobs_lease_expires_at")
        batch_op.drop_index("ix_ingestion_jobs_lease_token")
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("lease_token")
