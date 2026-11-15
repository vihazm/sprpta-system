"""complaint_targets

Classifies a complaint by who it is against (Driver, Conductor, Bus owner, Bus / Transport service, Other),
separately from who complained and from the issue category. Adds the list of target types, an optional
category-to-target link table (empty until the client approves mappings), and complaints.target_type_id.
Complaints that already name an accused person are classified by that person's type; the rest stay unclassified.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-15 11:32:55.445502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('complaint_target_types',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('code', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaint_target_types')),
    sa.UniqueConstraint('code', name=op.f('uq_complaint_target_types_code')),
    sa.UniqueConstraint('name', name=op.f('uq_complaint_target_types_name'))
    )
    op.create_table('complaint_category_targets',
    sa.Column('category_id', sa.BigInteger(), nullable=False),
    sa.Column('target_type_id', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['complaint_categories.id'], name=op.f('fk_complaint_category_targets_category_id_complaint_categories')),
    sa.ForeignKeyConstraint(['target_type_id'], ['complaint_target_types.id'], name=op.f('fk_complaint_category_targets_target_type_id_complaint_target_types')),
    sa.PrimaryKeyConstraint('category_id', 'target_type_id', name=op.f('pk_complaint_category_targets'))
    )
    op.add_column('complaints', sa.Column('target_type_id', sa.BigInteger(), nullable=True))
    op.create_index('ix_complaints_entered_by_target', 'complaints', ['entered_by_user_id', 'target_type_id'], unique=False)
    op.create_foreign_key(op.f('fk_complaints_target_type_id_complaint_target_types'), 'complaints', 'complaint_target_types', ['target_type_id'], ['id'])

    targets = sa.table('complaint_target_types', sa.column('code', sa.Text), sa.column('name', sa.Text), sa.column('sort_order', sa.SmallInteger))
    op.bulk_insert(targets, [
        {'code': 'driver', 'name': 'Driver', 'sort_order': 1},
        {'code': 'conductor', 'name': 'Conductor', 'sort_order': 2},
        {'code': 'owner', 'name': 'Bus owner', 'sort_order': 3},
        {'code': 'bus_service', 'name': 'Bus / Transport service', 'sort_order': 4},
        {'code': 'other', 'name': 'Other', 'sort_order': 5},
    ])
    # Complaints made before this change: classified by the type of the person they name, where there is one.
    op.execute(
        """
        UPDATE complaints c SET target_type_id = t.id
        FROM people p JOIN complaint_target_types t ON t.code = CASE p.person_type
            WHEN 'driver' THEN 'driver' WHEN 'conductor' THEN 'conductor' WHEN 'owner' THEN 'owner' ELSE 'other' END
        WHERE p.id = c.subject_person_id
        """
    )

def downgrade() -> None:
    op.drop_constraint(op.f('fk_complaints_target_type_id_complaint_target_types'), 'complaints', type_='foreignkey')
    op.drop_index('ix_complaints_entered_by_target', table_name='complaints')
    op.drop_column('complaints', 'target_type_id')
    op.drop_table('complaint_category_targets')
    op.drop_table('complaint_target_types')
