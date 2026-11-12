"""Column types shared by the models: one PostgreSQL enumeration per fixed list."""

from enum import StrEnum

from sqlalchemy import Enum

from app.core import enums


def pg_enum(cls: type[StrEnum], name: str) -> Enum:
    """A native PostgreSQL enumeration that stores the values (not the member names)."""
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


ComplaintStatusType = pg_enum(enums.ComplaintStatus, "complaint_status")
RejectionTypeType = pg_enum(enums.RejectionType, "rejection_type")
DuplicateLinkTypeType = pg_enum(enums.DuplicateLinkType, "duplicate_link_type")
DecisionActionType = pg_enum(enums.DecisionAction, "decision_action")
DecisionOutcomeType = pg_enum(enums.DecisionOutcome, "decision_outcome")
RecommendationTypeType = pg_enum(enums.RecommendationType, "recommendation_type")
RecommendationStatusType = pg_enum(enums.RecommendationStatus, "recommendation_status")
MessageTypeType = pg_enum(enums.MessageType, "message_type")
MessageChannelType = pg_enum(enums.MessageChannel, "message_channel")
MessageStateType = pg_enum(enums.MessageState, "message_state")
PersonTypeType = pg_enum(enums.PersonType, "person_type")
VehicleTypeType = pg_enum(enums.VehicleType, "vehicle_type")
PlaceKindType = pg_enum(enums.PlaceKind, "place_kind")
RatingBandType = pg_enum(enums.RatingBand, "rating_band")
AppealStatusType = pg_enum(enums.AppealStatus, "appeal_status")
