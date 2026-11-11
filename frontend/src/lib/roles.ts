// Roles, landing pages and side navigation (UI Flow Document, sections 1.2 and 1.3).
// Safe to import from server and client code. The backend remains the real
// authority on who may do what; this only shapes the interface.

export type Role = "l1" | "l2" | "l3" | "admin" | "implementing_staff" | "cp";

export const ROLE_LABEL: Record<Role, string> = {
  l1: "Level 1 Office Staff",
  l2: "Level 2 Area Officer",
  l3: "Level 3 Chairman",
  admin: "System Administrator",
  implementing_staff: "Implementing Staff",
  cp: "Complainant",
};

// Where each role lands after login. The backend returns the same path.
export const LANDING_PATH: Record<Role, string> = {
  l1: "/l1/dashboard",
  l2: "/l2/dashboard",
  l3: "/l3/dashboard",
  admin: "/admin/dashboard",
  implementing_staff: "/is/cases",
  cp: "/cp/complaints",
};

// First URL segment of each role's area, used for route guards.
export const ROLE_PREFIX: Record<Role, string> = {
  l1: "/l1",
  l2: "/l2",
  l3: "/l3",
  admin: "/admin",
  implementing_staff: "/is",
  cp: "/cp",
};

export const PROTECTED_PREFIXES = Object.values(ROLE_PREFIX);

export function isRole(value: unknown): value is Role {
  return typeof value === "string" && value in LANDING_PATH;
}

/** Which role's area a path belongs to, or null for public paths. */
export function roleForPath(pathname: string): Role | null {
  for (const role of Object.keys(ROLE_PREFIX) as Role[]) {
    const prefix = ROLE_PREFIX[role];
    if (pathname === prefix || pathname.startsWith(`${prefix}/`)) return role;
  }
  return null;
}

/**
 * Accept a ?next= target only if it is a path inside the signed-in role's own
 * area. Anything else (other sites, other roles, odd characters) is ignored,
 * so it cannot be used as an open redirect.
 */
export function safeNextPath(next: string | null | undefined, role: Role): string | null {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return null;
  return roleForPath(next.split("?")[0]) === role ? next : null;
}

export type NavItem = { label: string; href?: string };

// An item gets an href once its screen exists; until then it shows as "Soon".
export const NAV_ITEMS: Record<Role, NavItem[]> = {
  cp: [{ label: "My complaints", href: "/cp/complaints" }, { label: "New complaint" }],
  implementing_staff: [{ label: "Case search", href: "/is/cases" }],
  l1: [
    { label: "Dashboard", href: "/l1/dashboard" },
    { label: "Complaints" },
    { label: "Portal submissions" },
    { label: "New complaint" },
    { label: "New recommendation" },
  ],
  l2: [
    { label: "Dashboard", href: "/l2/dashboard" },
    { label: "Cases" },
    { label: "Recommendations" },
  ],
  l3: [
    { label: "Dashboard", href: "/l3/dashboard" },
    { label: "Statistics" },
    { label: "Escalated cases" },
    { label: "Recommendations" },
    { label: "Reports" },
    { label: "Audit trail" },
    { label: "Ratings" },
    { label: "Appeals" },
  ],
  admin: [
    { label: "Dashboard", href: "/admin/dashboard" },
    { label: "Users", href: "/admin/users" },
    { label: "Master data" },
    { label: "Message templates" },
    { label: "Policy documents" },
    { label: "Settings" },
    { label: "System health", href: "/admin/system-health" },
    { label: "Usage logs" },
    { label: "Statistics and reports" },
  ],
};
