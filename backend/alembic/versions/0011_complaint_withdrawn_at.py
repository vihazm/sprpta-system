"""complaint_withdrawn_at

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-25 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """A complainant can delete (withdraw) a portal complaint that Level 1 has not checked yet."""
    op.add_column('complaints', sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        op.f('ck_complaints_withdrawn_only_while_submitted'),
        'complaints',
        "withdrawn_at IS NULL OR status = 'submitted'",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('ck_complaints_withdrawn_only_while_submitted'), 'complaints', type_='check')
    op.drop_column('complaints', 'withdrawn_at')
