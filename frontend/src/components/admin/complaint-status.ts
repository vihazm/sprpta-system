import { STATUS_LABEL } from "@/components/l2/status";

// The names of the statuses a registered complaint can have, for the administrator's dashboard and statistics.
const STATUS_NAMES: Record<string, string> = { ...STATUS_LABEL, incomplete: "Incomplete", rejected: "Rejected" };

/** "under_review" becomes "Under review". */
export const statusName = (status: string) => STATUS_NAMES[status] ?? status;
