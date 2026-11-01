"""versioned procurement data for staged re-indexing

Revision ID: 20261022104000
Revises: 20261021150734
Create Date: 2026-10-22 10:40:00.000000

This migration adds version tracking (indexing_version and is_active) to
Price and ComplianceCertificate models so candidate facts can be persisted
during candidate ingestion without exposing them to active queries or overwriting
active version facts.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261022104000"
down_revision = "20261021150734"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. prices table versioning
    op.add_column(
        "prices",
        sa.Column(
            "indexing_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Document indexing version this price belongs to",
        ),
    )
    op.add_column(
        "prices",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="Whether this price is active for retrieval and reporting",
        ),
    )
    op.create_index(
        "ix_prices_version_active",
        "prices",
        ["source_document_id", "indexing_version", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_prices_indexing_version",
        "prices",
        ["indexing_version"],
        unique=False,
    )

    # 2. compliance_certificates table versioning
    op.add_column(
        "compliance_certificates",
        sa.Column(
            "indexing_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Document indexing version this certificate belongs to",
        ),
    )
    op.add_column(
        "compliance_certificates",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="Whether this certificate is active for retrieval and reporting",
        ),
    )
    op.create_index(
        "ix_compliance_certificates_version_active",
        "compliance_certificates",
        ["source_document_id", "indexing_version", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_compliance_certificates_indexing_version",
        "compliance_certificates",
        ["indexing_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_certificates_indexing_version", table_name="compliance_certificates")
    op.drop_index("ix_compliance_certificates_version_active", table_name="compliance_certificates")
    op.drop_column("compliance_certificates", "is_active")
    op.drop_column("compliance_certificates", "indexing_version")

    op.drop_index("ix_prices_indexing_version", table_name="prices")
    op.drop_index("ix_prices_version_active", table_name="prices")
    op.drop_column("prices", "is_active")
    op.drop_column("prices", "indexing_version")
