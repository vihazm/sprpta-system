"""duty_records

Daily operation records for the Bus & Permit Lookup: daily_trips (which bus ran which trip on a
date), trip_duties (who was on duty) and owner_assignments (who owned a bus over a period).
Only System Admin approves and publishes them; Level 1 reads the published ones.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Two tables share this type, so it is created once, up front, and the columns only refer to it.
STATUSES = ('draft', 'approved', 'published')


def _status() -> postgresql.ENUM:
    return postgresql.ENUM(*STATUSES, name='duty_record_status', create_type=False)


def upgrade() -> None:
    postgresql.ENUM(*STATUSES, name='duty_record_status').create(op.get_bind())

    op.create_table('owner_assignments',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('vehicle_id', sa.BigInteger(), nullable=False),
    sa.Column('owner_person_id', sa.BigInteger(), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_to', sa.Date(), nullable=True),
    sa.Column('status', _status(), server_default='draft', nullable=False),
    sa.Column('created_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('approved_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('published_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status <> 'published' OR (published_by_user_id IS NOT NULL AND published_at IS NOT NULL)", name=op.f('ck_owner_assignments_published_has_publisher')),
    sa.CheckConstraint("status = 'draft' OR (approved_by_user_id IS NOT NULL AND approved_at IS NOT NULL)", name=op.f('ck_owner_assignments_approved_has_approver')),
    sa.CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name=op.f('ck_owner_assignments_valid_period')),
    sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], name=op.f('fk_owner_assignments_approved_by_user_id_users')),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_owner_assignments_created_by_user_id_users')),
    sa.ForeignKeyConstraint(['owner_person_id'], ['people.id'], name=op.f('fk_owner_assignments_owner_person_id_people')),
    sa.ForeignKeyConstraint(['published_by_user_id'], ['users.id'], name=op.f('fk_owner_assignments_published_by_user_id_users')),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], name=op.f('fk_owner_assignments_vehicle_id_vehicles')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_owner_assignments'))
    )
    op.create_index('ix_owner_assignments_vehicle_from', 'owner_assignments', ['vehicle_id', 'valid_from'], unique=False)
    op.create_table('daily_trips',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('vehicle_id', sa.BigInteger(), nullable=False),
    sa.Column('permit_id', sa.BigInteger(), nullable=False),
    sa.Column('route_stand_id', sa.BigInteger(), nullable=False),
    sa.Column('departure_time', sa.Time(), nullable=False),
    sa.Column('origin', sa.Text(), nullable=False),
    sa.Column('destination', sa.Text(), nullable=False),
    sa.Column('status', _status(), server_default='draft', nullable=False),
    sa.Column('created_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('approved_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('published_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status <> 'published' OR (published_by_user_id IS NOT NULL AND published_at IS NOT NULL)", name=op.f('ck_daily_trips_published_has_publisher')),
    sa.CheckConstraint("status = 'draft' OR (approved_by_user_id IS NOT NULL AND approved_at IS NOT NULL)", name=op.f('ck_daily_trips_approved_has_approver')),
    sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], name=op.f('fk_daily_trips_approved_by_user_id_users')),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_daily_trips_created_by_user_id_users')),
    sa.ForeignKeyConstraint(['permit_id'], ['permits.id'], name=op.f('fk_daily_trips_permit_id_permits')),
    sa.ForeignKeyConstraint(['published_by_user_id'], ['users.id'], name=op.f('fk_daily_trips_published_by_user_id_users')),
    sa.ForeignKeyConstraint(['route_stand_id'], ['routes_stands.id'], name=op.f('fk_daily_trips_route_stand_id_routes_stands')),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], name=op.f('fk_daily_trips_vehicle_id_vehicles')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_daily_trips')),
    sa.UniqueConstraint('service_date', 'vehicle_id', 'departure_time', name='uq_daily_trips_service_date_vehicle_id_departure_time')
    )
    op.create_index('ix_daily_trips_date_status', 'daily_trips', ['service_date', 'status'], unique=False)
    op.create_index('ix_daily_trips_vehicle_date', 'daily_trips', ['vehicle_id', 'service_date'], unique=False)
    op.create_table('trip_duties',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('trip_id', sa.BigInteger(), nullable=False),
    sa.Column('driver_person_id', sa.BigInteger(), nullable=True),
    sa.Column('conductor_person_id', sa.BigInteger(), nullable=True),
    sa.Column('verified_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(verified_by_user_id IS NULL) = (verified_at IS NULL)', name=op.f('ck_trip_duties_verification_complete')),
    sa.ForeignKeyConstraint(['conductor_person_id'], ['people.id'], name=op.f('fk_trip_duties_conductor_person_id_people')),
    sa.ForeignKeyConstraint(['driver_person_id'], ['people.id'], name=op.f('fk_trip_duties_driver_person_id_people')),
    sa.ForeignKeyConstraint(['trip_id'], ['daily_trips.id'], name=op.f('fk_trip_duties_trip_id_daily_trips')),
    sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.id'], name=op.f('fk_trip_duties_verified_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trip_duties')),
    sa.UniqueConstraint('trip_id', name=op.f('uq_trip_duties_trip_id'))
    )

def downgrade() -> None:
    op.drop_table('trip_duties')
    op.drop_index('ix_daily_trips_vehicle_date', table_name='daily_trips')
    op.drop_index('ix_daily_trips_date_status', table_name='daily_trips')
    op.drop_table('daily_trips')
    op.drop_index('ix_owner_assignments_vehicle_from', table_name='owner_assignments')
    op.drop_table('owner_assignments')
    _status().drop(op.get_bind())
