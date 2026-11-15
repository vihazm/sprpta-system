"""daily_record_entry

Lets Level 1 officers enter daily bus operation records (kept as drafts, shown as Pending Verification until System
Admin approves and publishes them). Adds the trip end time, remarks and the owner named on the record to daily_trips,
the duty start and end times of the driver and conductor to trip_duties, and an index for "my records".

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-15 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('daily_trips', sa.Column('end_time', sa.Time(), nullable=True))
    op.add_column('daily_trips', sa.Column('remarks', sa.Text(), nullable=True))
    op.add_column('daily_trips', sa.Column('owner_person_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(op.f('fk_daily_trips_owner_person_id_people'), 'daily_trips', 'people', ['owner_person_id'], ['id'])
    op.create_index('ix_daily_trips_created_by_date', 'daily_trips', ['created_by_user_id', 'service_date'], unique=False)
    op.add_column('trip_duties', sa.Column('driver_start', sa.Time(), nullable=True))
    op.add_column('trip_duties', sa.Column('driver_end', sa.Time(), nullable=True))
    op.add_column('trip_duties', sa.Column('conductor_start', sa.Time(), nullable=True))
    op.add_column('trip_duties', sa.Column('conductor_end', sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column('trip_duties', 'conductor_end')
    op.drop_column('trip_duties', 'conductor_start')
    op.drop_column('trip_duties', 'driver_end')
    op.drop_column('trip_duties', 'driver_start')
    op.drop_index('ix_daily_trips_created_by_date', table_name='daily_trips')
    op.drop_constraint(op.f('fk_daily_trips_owner_person_id_people'), 'daily_trips', type_='foreignkey')
    op.drop_column('daily_trips', 'owner_person_id')
    op.drop_column('daily_trips', 'remarks')
    op.drop_column('daily_trips', 'end_time')
