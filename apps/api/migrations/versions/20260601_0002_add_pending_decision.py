from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260601_0002"
down_revision: str | None = "20260601_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("pending_decision_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "pending_decision_json")
