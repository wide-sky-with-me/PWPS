from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260601_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=True),
        sa.Column("raw_input", sa.String(), nullable=False),
        sa.Column("workflow_state_json", sa.JSON(), nullable=False),
        sa.Column("outputs_json", sa.JSON(), nullable=False),
        sa.Column("trace_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )


def downgrade() -> None:
    op.drop_table("runs")
