// 2026-11-14 becomes 14 Nov 2026.
export function formatDay(date: string) {
  return new Date(`${date}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

// The route number is the first part of the route's name ("24/1 Avithtawa - Elpitiya" is route 24/1). A route
// with no number in its name has none to show.
export function routeNumber(routeName: string): string | null {
  const first = routeName.trim().split(/\s+/)[0] ?? "";
  return /\d/.test(first) ? first : null;
}
