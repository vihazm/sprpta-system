import { notify } from "@/lib/notify";
import type { BusRecord } from "@/components/l1/entry/types";
import { recordSummary } from "./RecordFields";

/** Copy Details: the record as readable text, with the common popup to say what happened. */
export async function copyRecord(record: BusRecord) {
  try {
    await navigator.clipboard.writeText(recordSummary(record));
    notify.success("Bus details copied", `${record.busNumber}, trip at ${record.departure}.`);
  } catch {
    notify.error("Could not copy", "Your browser did not allow it. Select the details and copy them by hand.");
  }
}