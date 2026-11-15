"""complaint_duty_snapshots

What the verified daily record said when a complaint was saved against it (so the complaint keeps showing
who was on duty), plus the incident time and location that the Level 1 complaint form asks for.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('complaint_duty_snapshots',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=False),
    sa.Column('trip_id', sa.BigInteger(), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('bus_number', sa.Text(), nullable=False),
    sa.Column('permit_number', sa.Text(), nullable=False),
    sa.Column('route_name', sa.Text(), nullable=False),
    sa.Column('origin', sa.Text(), nullable=False),
    sa.Column('destination', sa.Text(), nullable=False),
    sa.Column('departure_time', sa.Time(), nullable=False),
    sa.Column('owner_person_id', sa.BigInteger(), nullable=True),
    sa.Column('owner_name', sa.Text(), nullable=True),
    sa.Column('driver_person_id', sa.BigInteger(), nullable=True),
    sa.Column('driver_name', sa.Text(), nullable=True),
    sa.Column('conductor_person_id', sa.BigInteger(), nullable=True),
    sa.Column('conductor_name', sa.Text(), nullable=True),
    sa.Column('verification_status', sa.Text(), nullable=False),
    sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("verification_status IN ('Verified', 'Unverified', 'Unavailable')", name=op.f('ck_complaint_duty_snapshots_known_verification_status')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_complaint_duty_snapshots_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['conductor_person_id'], ['people.id'], name=op.f('fk_complaint_duty_snapshots_conductor_person_id_people')),
    sa.ForeignKeyConstraint(['driver_person_id'], ['people.id'], name=op.f('fk_complaint_duty_snapshots_driver_person_id_people')),
    sa.ForeignKeyConstraint(['owner_person_id'], ['people.id'], name=op.f('fk_complaint_duty_snapshots_owner_person_id_people')),
    sa.ForeignKeyConstraint(['trip_id'], ['daily_trips.id'], name=op.f('fk_complaint_duty_snapshots_trip_id_daily_trips')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaint_duty_snapshots')),
    sa.UniqueConstraint('complaint_id', name=op.f('uq_complaint_duty_snapshots_complaint_id'))
    )
    op.add_column('complaints', sa.Column('incident_time', sa.Time(), nullable=True))
    op.add_column('complaints', sa.Column('incident_location', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('complaints', 'incident_location')
    op.drop_column('complaints', 'incident_time')
    op.drop_table('complaint_duty_snapshots')
