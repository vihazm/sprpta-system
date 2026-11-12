"""core_tables

The remaining non-AI tables of the Database Structure Document: master data,
the complaint core, recommendations, messaging, audit log, settings and rating.
The AI (RAG) tables are left for the module that needs them.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Fixed lists (DB doc 1.2). Several tables share one type, so the types are
# created once, up front, and the columns only refer to them.
ENUMS = {
    'complaint_status': ('draft', 'submitted', 'incomplete', 'forwarded', 'under_review', 'awaiting_implementation', 'done_awaiting_approval', 'escalated', 'closed', 'rejected'),
    'rejection_type': ('invalid', 'spam', 'out_of_jurisdiction', 'duplicate'),
    'duplicate_link_type': ('not_duplicate', 'duplicate_of', 'related'),
    'decision_action': ('warning', 'fine', 'suspension', 'legal_action', 'no_action'),
    'decision_outcome': ('substantiated', 'partly_substantiated', 'not_substantiated'),
    'recommendation_type': ('improvement', 'commendation'),
    'recommendation_status': ('new', 'acknowledged', 'under_consideration', 'accepted_implemented', 'declined', 'commendation_verified'),
    'message_type': ('registered', 'decided', 'closed', 'otp'),
    'message_channel': ('sms', 'email'),
    'message_state': ('sent', 'failed'),
    'person_type': ('driver', 'conductor', 'sprpta_staff', 'owner'),
    'vehicle_type': ('bus', 'trishaw'),
    'place_kind': ('route', 'stand'),
    'rating_band': ('excellent', 'good', 'needs_improvement', 'poor'),
    'appeal_status': ('open', 'resolved'),
}


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def _protect_audit_log() -> None:
    """DB doc 5.1: audit_log is append-only. A trigger rejects any UPDATE or DELETE.

    The application's database role should also be limited to INSERT and
    SELECT on this table; that grant is made when the app gets its own role.
    """
    op.execute(
        """
        CREATE FUNCTION audit_log_block_changes() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER audit_log_append_only BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_block_changes()"
    )


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind)

    op.create_table('complaint_categories',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaint_categories')),
    sa.UniqueConstraint('name', name=op.f('uq_complaint_categories_name'))
    )
    op.create_table('complaint_mediums',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('is_system', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaint_mediums')),
    sa.UniqueConstraint('name', name=op.f('uq_complaint_mediums_name'))
    )
    op.create_table('people',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('full_name', sa.Text(), nullable=False),
    sa.Column('person_type', _enum('person_type'), nullable=False),
    sa.Column('staff_number', sa.Text(), nullable=True),
    sa.Column('phone', sa.Text(), nullable=True),
    sa.Column('team_label', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_people'))
    )
    op.create_table('severities',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('rank', sa.SmallInteger(), nullable=False),
    sa.Column('forward_days', sa.Integer(), nullable=False),
    sa.Column('decide_days', sa.Integer(), nullable=False),
    sa.Column('close_days', sa.Integer(), nullable=False),
    sa.Column('rating_weight', sa.Numeric(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_severities')),
    sa.UniqueConstraint('name', name=op.f('uq_severities_name'))
    )
    op.create_table('otp_codes',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complainant_account_id', sa.BigInteger(), nullable=False),
    sa.Column('channel', _enum('message_channel'), nullable=False),
    sa.Column('code_hash', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['complainant_account_id'], ['complainant_accounts.id'], name=op.f('fk_otp_codes_complainant_account_id_complainant_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_otp_codes'))
    )
    op.create_table('rating_snapshots',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('person_id', sa.BigInteger(), nullable=False),
    sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('window_start', sa.Date(), nullable=False),
    sa.Column('window_end', sa.Date(), nullable=False),
    sa.Column('penalty', sa.Numeric(), nullable=False),
    sa.Column('credits', sa.Integer(), nullable=False),
    sa.Column('score', sa.Numeric(), nullable=False),
    sa.Column('band', _enum('rating_band'), nullable=False),
    sa.Column('formula_version', sa.Integer(), nullable=False),
    sa.Column('breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('trigger', sa.Text(), nullable=False),
    sa.CheckConstraint('score >= 0 AND score <= 100', name=op.f('ck_rating_snapshots_score_in_range')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_rating_snapshots_person_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rating_snapshots'))
    )
    op.create_index('ix_rating_snapshots_person_computed', 'rating_snapshots', ['person_id', sa.literal_column('computed_at DESC')], unique=False)
    op.create_table('routes_stands',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('kind', _enum('place_kind'), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('area_id', sa.BigInteger(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['area_id'], ['areas.id'], name=op.f('fk_routes_stands_area_id_areas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_routes_stands')),
    sa.UniqueConstraint('kind', 'name', 'area_id', name='uq_routes_stands_kind_name_area_id')
    )
    op.create_table('vehicles',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('vehicle_number', sa.Text(), nullable=False),
    sa.Column('vehicle_type', _enum('vehicle_type'), nullable=False),
    sa.Column('registered_area_id', sa.BigInteger(), nullable=False),
    sa.Column('owner_person_id', sa.BigInteger(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_person_id'], ['people.id'], name=op.f('fk_vehicles_owner_person_id_people')),
    sa.ForeignKeyConstraint(['registered_area_id'], ['areas.id'], name=op.f('fk_vehicles_registered_area_id_areas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vehicles')),
    sa.UniqueConstraint('vehicle_number', name=op.f('uq_vehicles_vehicle_number'))
    )
    op.create_table('message_templates',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('message_type', _enum('message_type'), nullable=False),
    sa.Column('channel', _enum('message_channel'), nullable=False),
    sa.Column('subject', sa.Text(), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('updated_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name=op.f('fk_message_templates_updated_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_message_templates')),
    sa.UniqueConstraint('message_type', 'channel', name='uq_message_templates_type_channel')
    )
    op.create_table('permits',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('permit_number', sa.Text(), nullable=False),
    sa.Column('vehicle_id', sa.BigInteger(), nullable=False),
    sa.Column('holder_person_id', sa.BigInteger(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['holder_person_id'], ['people.id'], name=op.f('fk_permits_holder_person_id_people')),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], name=op.f('fk_permits_vehicle_id_vehicles')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_permits')),
    sa.UniqueConstraint('permit_number', name=op.f('uq_permits_permit_number'))
    )
    op.create_table('recommendations',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('recommendation_type', _enum('recommendation_type'), nullable=False),
    sa.Column('status', _enum('recommendation_status'), server_default='new', nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('details', sa.Text(), nullable=False),
    sa.Column('medium_id', sa.BigInteger(), nullable=True),
    sa.Column('received_date', sa.Date(), nullable=True),
    sa.Column('subject_person_id', sa.BigInteger(), nullable=True),
    sa.Column('entered_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('status_changed_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('status_changed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("recommendation_type = 'commendation' OR subject_person_id IS NULL", name=op.f('ck_recommendations_person_only_for_commendation')),
    sa.CheckConstraint("status <> 'commendation_verified' OR recommendation_type = 'commendation'", name=op.f('ck_recommendations_verified_only_for_commendation')),
    sa.ForeignKeyConstraint(['entered_by_user_id'], ['users.id'], name=op.f('fk_recommendations_entered_by_user_id_users')),
    sa.ForeignKeyConstraint(['medium_id'], ['complaint_mediums.id'], name=op.f('fk_recommendations_medium_id_complaint_mediums')),
    sa.ForeignKeyConstraint(['status_changed_by_user_id'], ['users.id'], name=op.f('fk_recommendations_status_changed_by_user_id_users')),
    sa.ForeignKeyConstraint(['subject_person_id'], ['people.id'], name=op.f('fk_recommendations_subject_person_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recommendations'))
    )
    op.create_table('system_settings',
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('updated_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name=op.f('fk_system_settings_updated_by_user_id_users')),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_system_settings'))
    )
    op.create_table('complaints',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('reference_number', sa.Text(), nullable=True),
    sa.Column('status', _enum('complaint_status'), server_default='draft', nullable=False),
    sa.Column('submitted_via_portal', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('complainant_account_id', sa.BigInteger(), nullable=True),
    sa.Column('entered_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('checked_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('medium_id', sa.BigInteger(), nullable=True),
    sa.Column('is_anonymous', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('complainant_name', sa.Text(), nullable=True),
    sa.Column('contact_phone', sa.Text(), nullable=True),
    sa.Column('contact_email', sa.Text(), nullable=True),
    sa.Column('complaint_date', sa.Date(), nullable=True),
    sa.Column('subject', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('category_id', sa.BigInteger(), nullable=True),
    sa.Column('severity_id', sa.BigInteger(), nullable=True),
    sa.Column('subject_person_id', sa.BigInteger(), nullable=True),
    sa.Column('subject_person_text', sa.Text(), nullable=True),
    sa.Column('vehicle_number_entered', sa.Text(), nullable=True),
    sa.Column('vehicle_id', sa.BigInteger(), nullable=True),
    sa.Column('permit_id', sa.BigInteger(), nullable=True),
    sa.Column('owner_person_id', sa.BigInteger(), nullable=True),
    sa.Column('route_stand_id', sa.BigInteger(), nullable=True),
    sa.Column('area_id', sa.BigInteger(), nullable=True),
    sa.Column('assigned_l2_user_id', sa.BigInteger(), nullable=True),
    sa.Column('rejection_type', _enum('rejection_type'), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('duplicate_of_complaint_id', sa.BigInteger(), nullable=True),
    sa.Column('registered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('forwarded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('escalated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('paused_since', sa.DateTime(timezone=True), nullable=True),
    sa.Column('paused_total', sa.Interval(), server_default=sa.text("interval '0'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("rejection_type IS DISTINCT FROM 'duplicate' OR duplicate_of_complaint_id IS NOT NULL", name=op.f('ck_complaints_duplicate_has_earlier_case')),
    sa.CheckConstraint("status <> 'rejected' OR (rejection_type IS NOT NULL AND rejection_reason IS NOT NULL)", name=op.f('ck_complaints_rejected_has_reason')),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'rejected') OR reference_number IS NOT NULL", name=op.f('ck_complaints_reference_number_issued')),
    sa.CheckConstraint("status NOT IN ('forwarded', 'under_review', 'awaiting_implementation', 'done_awaiting_approval', 'escalated', 'closed') OR (severity_id IS NOT NULL AND category_id IS NOT NULL AND medium_id IS NOT NULL AND vehicle_id IS NOT NULL AND area_id IS NOT NULL AND assigned_l2_user_id IS NOT NULL)", name=op.f('ck_complaints_routed_has_details')),
    sa.CheckConstraint('NOT is_anonymous OR (complainant_name IS NULL AND contact_phone IS NULL AND contact_email IS NULL)', name=op.f('ck_complaints_anonymous_has_no_contact')),
    sa.ForeignKeyConstraint(['area_id'], ['areas.id'], name=op.f('fk_complaints_area_id_areas')),
    sa.ForeignKeyConstraint(['assigned_l2_user_id'], ['users.id'], name=op.f('fk_complaints_assigned_l2_user_id_users')),
    sa.ForeignKeyConstraint(['category_id'], ['complaint_categories.id'], name=op.f('fk_complaints_category_id_complaint_categories')),
    sa.ForeignKeyConstraint(['checked_by_user_id'], ['users.id'], name=op.f('fk_complaints_checked_by_user_id_users')),
    sa.ForeignKeyConstraint(['complainant_account_id'], ['complainant_accounts.id'], name=op.f('fk_complaints_complainant_account_id_complainant_accounts')),
    sa.ForeignKeyConstraint(['duplicate_of_complaint_id'], ['complaints.id'], name=op.f('fk_complaints_duplicate_of_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['entered_by_user_id'], ['users.id'], name=op.f('fk_complaints_entered_by_user_id_users')),
    sa.ForeignKeyConstraint(['medium_id'], ['complaint_mediums.id'], name=op.f('fk_complaints_medium_id_complaint_mediums')),
    sa.ForeignKeyConstraint(['owner_person_id'], ['people.id'], name=op.f('fk_complaints_owner_person_id_people')),
    sa.ForeignKeyConstraint(['permit_id'], ['permits.id'], name=op.f('fk_complaints_permit_id_permits')),
    sa.ForeignKeyConstraint(['route_stand_id'], ['routes_stands.id'], name=op.f('fk_complaints_route_stand_id_routes_stands')),
    sa.ForeignKeyConstraint(['severity_id'], ['severities.id'], name=op.f('fk_complaints_severity_id_severities')),
    sa.ForeignKeyConstraint(['subject_person_id'], ['people.id'], name=op.f('fk_complaints_subject_person_id_people')),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], name=op.f('fk_complaints_vehicle_id_vehicles')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaints')),
    sa.UniqueConstraint('reference_number', name=op.f('uq_complaints_reference_number'))
    )
    op.create_index('ix_complaints_area_status', 'complaints', ['area_id', 'status'], unique=False)
    op.create_index('ix_complaints_complainant_account', 'complaints', ['complainant_account_id'], unique=False)
    op.create_index('ix_complaints_l2_officer_status', 'complaints', ['assigned_l2_user_id', 'status'], unique=False)
    op.create_index('ix_complaints_severity_registered', 'complaints', ['severity_id', 'registered_at'], unique=False)
    op.create_index('ix_complaints_status', 'complaints', ['status'], unique=False)
    op.create_index('ix_complaints_subject_person', 'complaints', ['subject_person_id'], unique=False)
    op.create_index('ix_complaints_vehicle', 'complaints', ['vehicle_id'], unique=False)
    op.create_table('audit_log',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('actor_user_id', sa.BigInteger(), nullable=True),
    sa.Column('actor_account_id', sa.BigInteger(), nullable=True),
    sa.Column('actor_role', sa.Text(), nullable=False),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('entity_type', sa.Text(), nullable=False),
    sa.Column('entity_id', sa.BigInteger(), nullable=True),
    sa.Column('complaint_id', sa.BigInteger(), nullable=True),
    sa.Column('from_status', _enum('complaint_status'), nullable=True),
    sa.Column('to_status', _enum('complaint_status'), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['actor_account_id'], ['complainant_accounts.id'], name=op.f('fk_audit_log_actor_account_id_complainant_accounts')),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_audit_log_actor_user_id_users')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_audit_log_complaint_id_complaints')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_index('ix_audit_log_action', 'audit_log', ['action'], unique=False)
    op.create_index('ix_audit_log_actor_user_occurred', 'audit_log', ['actor_user_id', 'occurred_at'], unique=False)
    op.create_index('ix_audit_log_complaint_occurred', 'audit_log', ['complaint_id', 'occurred_at'], unique=False)
    op.create_table('case_decisions',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=False),
    sa.Column('decided_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('action', _enum('decision_action'), nullable=False),
    sa.Column('reasoning', sa.Text(), nullable=False),
    sa.Column('outcome', _enum('decision_outcome'), nullable=False),
    sa.Column('ai_suggestion_id', sa.BigInteger(), nullable=True),
    sa.Column('ai_followed', sa.Boolean(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('ai_suggestion_id IS NOT NULL OR ai_followed IS NULL', name=op.f('ck_case_decisions_followed_needs_suggestion')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_case_decisions_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.id'], name=op.f('fk_case_decisions_decided_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_case_decisions')),
    sa.UniqueConstraint('complaint_id', name=op.f('uq_case_decisions_complaint_id'))
    )
    op.create_table('complaint_attachments',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=False),
    sa.Column('file_name', sa.Text(), nullable=False),
    sa.Column('storage_path', sa.Text(), nullable=False),
    sa.Column('mime_type', sa.Text(), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('uploaded_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('uploaded_by_account_id', sa.BigInteger(), nullable=True),
    sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('num_nonnulls(uploaded_by_user_id, uploaded_by_account_id) = 1', name=op.f('ck_complaint_attachments_one_uploader')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_complaint_attachments_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['uploaded_by_account_id'], ['complainant_accounts.id'], name=op.f('fk_complaint_attachments_uploaded_by_account_id_accounts')),
    sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], name=op.f('fk_complaint_attachments_uploaded_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaint_attachments'))
    )
    op.create_table('duplicate_checks',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=False),
    sa.Column('candidate_complaint_id', sa.BigInteger(), nullable=False),
    sa.Column('link_type', _enum('duplicate_link_type'), nullable=False),
    sa.Column('decided_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('decided_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('complaint_id <> candidate_complaint_id', name=op.f('ck_duplicate_checks_not_itself')),
    sa.ForeignKeyConstraint(['candidate_complaint_id'], ['complaints.id'], name=op.f('fk_duplicate_checks_candidate_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_duplicate_checks_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.id'], name=op.f('fk_duplicate_checks_decided_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_duplicate_checks')),
    sa.UniqueConstraint('complaint_id', 'candidate_complaint_id', name='uq_duplicate_checks_complaint_candidate')
    )
    op.create_table('escalations',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=False),
    sa.Column('escalated_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('escalated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(reason) > 0', name=op.f('ck_escalations_reason_not_empty')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_escalations_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['escalated_by_user_id'], ['users.id'], name=op.f('fk_escalations_escalated_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_escalations')),
    sa.UniqueConstraint('complaint_id', name=op.f('uq_escalations_complaint_id'))
    )
    op.create_table('outbound_messages',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=True),
    sa.Column('complainant_account_id', sa.BigInteger(), nullable=True),
    sa.Column('message_type', _enum('message_type'), nullable=False),
    sa.Column('channel', _enum('message_channel'), nullable=False),
    sa.Column('recipient', sa.Text(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('state', _enum('message_state'), nullable=False),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("message_type = 'otp' OR complaint_id IS NOT NULL", name=op.f('ck_outbound_messages_case_message_has_complaint')),
    sa.ForeignKeyConstraint(['complainant_account_id'], ['complainant_accounts.id'], name=op.f('fk_outbound_messages_complainant_account_id_accounts')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_outbound_messages_complaint_id_complaints')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_outbound_messages'))
    )
    op.create_index('uq_outbound_messages_one_sent_per_case', 'outbound_messages', ['complaint_id', 'message_type'], unique=True, postgresql_where=sa.text("state = 'sent' AND message_type <> 'otp'"))
    op.create_table('rating_appeals',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('person_id', sa.BigInteger(), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('status', _enum('appeal_status'), server_default='open', nullable=False),
    sa.Column('recorded_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('lodged_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('resolved_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolution', sa.Text(), nullable=True),
    sa.Column('snapshot_before_id', sa.BigInteger(), nullable=True),
    sa.Column('snapshot_after_id', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_rating_appeals_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_rating_appeals_person_id_people')),
    sa.ForeignKeyConstraint(['recorded_by_user_id'], ['users.id'], name=op.f('fk_rating_appeals_recorded_by_user_id_users')),
    sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], name=op.f('fk_rating_appeals_resolved_by_user_id_users')),
    sa.ForeignKeyConstraint(['snapshot_after_id'], ['rating_snapshots.id'], name=op.f('fk_rating_appeals_snapshot_after_id_rating_snapshots')),
    sa.ForeignKeyConstraint(['snapshot_before_id'], ['rating_snapshots.id'], name=op.f('fk_rating_appeals_snapshot_before_id_rating_snapshots')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rating_appeals'))
    )
    op.create_table('solution_documents',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=False),
    sa.Column('decision_id', sa.BigInteger(), nullable=False),
    sa.Column('summary_text', sa.Text(), nullable=False),
    sa.Column('verdict_text', sa.Text(), nullable=False),
    sa.Column('solution_details', sa.Text(), nullable=True),
    sa.Column('pdf_path', sa.Text(), nullable=False),
    sa.Column('generated_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_solution_documents_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['decision_id'], ['case_decisions.id'], name=op.f('fk_solution_documents_decision_id_case_decisions')),
    sa.ForeignKeyConstraint(['generated_by_user_id'], ['users.id'], name=op.f('fk_solution_documents_generated_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_solution_documents')),
    sa.UniqueConstraint('complaint_id', name=op.f('uq_solution_documents_complaint_id'))
    )
    op.create_table('implementation_records',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('complaint_id', sa.BigInteger(), nullable=False),
    sa.Column('solution_document_id', sa.BigInteger(), nullable=False),
    sa.Column('done_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('done_note', sa.Text(), nullable=False),
    sa.Column('done_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('approved_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('(approved_by_user_id IS NULL) = (approved_at IS NULL)', name=op.f('ck_implementation_records_approval_complete')),
    sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], name=op.f('fk_implementation_records_approved_by_user_id_users')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_implementation_records_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['done_by_user_id'], ['users.id'], name=op.f('fk_implementation_records_done_by_user_id_users')),
    sa.ForeignKeyConstraint(['solution_document_id'], ['solution_documents.id'], name=op.f('fk_implementation_records_solution_document_id_solution_docs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_implementation_records')),
    sa.UniqueConstraint('complaint_id', name=op.f('uq_implementation_records_complaint_id'))
    )
    _protect_audit_log()


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_append_only ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_block_changes()")
    op.drop_table('implementation_records')
    op.drop_table('solution_documents')
    op.drop_table('rating_appeals')
    op.drop_index('uq_outbound_messages_one_sent_per_case', table_name='outbound_messages', postgresql_where=sa.text("state = 'sent' AND message_type <> 'otp'"))
    op.drop_table('outbound_messages')
    op.drop_table('escalations')
    op.drop_table('duplicate_checks')
    op.drop_table('complaint_attachments')
    op.drop_table('case_decisions')
    op.drop_index('ix_audit_log_complaint_occurred', table_name='audit_log')
    op.drop_index('ix_audit_log_actor_user_occurred', table_name='audit_log')
    op.drop_index('ix_audit_log_action', table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index('ix_complaints_vehicle', table_name='complaints')
    op.drop_index('ix_complaints_subject_person', table_name='complaints')
    op.drop_index('ix_complaints_status', table_name='complaints')
    op.drop_index('ix_complaints_severity_registered', table_name='complaints')
    op.drop_index('ix_complaints_l2_officer_status', table_name='complaints')
    op.drop_index('ix_complaints_complainant_account', table_name='complaints')
    op.drop_index('ix_complaints_area_status', table_name='complaints')
    op.drop_table('complaints')
    op.drop_table('system_settings')
    op.drop_table('recommendations')
    op.drop_table('permits')
    op.drop_table('message_templates')
    op.drop_table('vehicles')
    op.drop_table('routes_stands')
    op.drop_index('ix_rating_snapshots_person_computed', table_name='rating_snapshots')
    op.drop_table('rating_snapshots')
    op.drop_table('otp_codes')
    op.drop_table('severities')
    op.drop_table('people')
    op.drop_table('complaint_mediums')
    op.drop_table('complaint_categories')

    bind = op.get_bind()
    for name, values in reversed(list(ENUMS.items())):
        postgresql.ENUM(*values, name=name).drop(bind)
