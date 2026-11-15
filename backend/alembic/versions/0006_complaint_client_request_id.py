"""complaint_client_request_id

A key the Level 1 form sends once per new complaint. If a save is retried (a lost response, a double click that
got through), the same key finds the complaint already created instead of making a second one.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-15 11:12:14.876978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('complaints', sa.Column('client_request_id', sa.Text(), nullable=True))
    op.create_index('uq_complaints_entered_by_client_request', 'complaints', ['entered_by_user_id', 'client_request_id'], unique=True, postgresql_where=sa.text('client_request_id IS NOT NULL'))


def downgrade() -> None:
    op.drop_index('uq_complaints_entered_by_client_request', table_name='complaints', postgresql_where=sa.text('client_request_id IS NOT NULL'))
    op.drop_column('complaints', 'client_request_id')
