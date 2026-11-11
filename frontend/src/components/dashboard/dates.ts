// Dates are shown in Sri Lankan time, whatever the server's or browser's own zone is.
export const TIME_ZONE = "Asia/Colombo";

/** "Wednesday, 11 November 2026" */
export function formatToday(now: Date) {
  return now.toLocaleDateString("en-GB", {
    timeZone: TIME_ZONE,
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** "Good morning, Nadeesha." The first word of the person's name is used. */
export function greeting(fullName: string, now: Date) {
  const hour = Number(
    now.toLocaleTimeString("en-GB", { timeZone: TIME_ZONE, hour: "2-digit", hour12: false }).slice(0, 2),
  );
  const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  return `Good ${part}, ${fullName.split(" ")[0]}.`;
}
