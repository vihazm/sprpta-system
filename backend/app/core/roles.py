"""Roles and where each one lands after login (UI Flow section 1.2, UC-C01)."""

from enum import StrEnum


class UserRole(StrEnum):
    """Values of the `user_role` database enumeration (staff accounts)."""

    L1 = "l1"
    L2 = "l2"
    L3 = "l3"
    ADMIN = "admin"
    IMPLEMENTING_STAFF = "implementing_staff"


# Complainant portal users are not in `user_role`: they live in a separate
# table so a public account can never carry a staff role.
COMPLAINANT_ROLE = "cp"

LANDING_PATHS: dict[str, str] = {
    UserRole.L1: "/l1/dashboard",
    UserRole.L2: "/l2/dashboard",
    UserRole.L3: "/l3/dashboard",
    UserRole.ADMIN: "/admin/dashboard",
    UserRole.IMPLEMENTING_STAFF: "/is/cases",  # IS lands on case search
    COMPLAINANT_ROLE: "/cp/complaints",  # CP lands on My complaints
}


def landing_path(role: str) -> str:
    return LANDING_PATHS[role]
