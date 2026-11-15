"use client";

import { useState, type FormEvent } from "react";
import { Field, inputClass } from "@/components/dashboard/controls";
import { Note } from "@/components/dashboard/Note";
import { Chip, PillButton, muted } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
import { loadTrip, searchTrips } from "./api";
import { formatDay } from "./format";
import { SelectedRecord } from "./SelectedRecord";
import type { BusSearch, TripDetails } from "./types";

const REASONS: Record<string, string> = {
  maintenance: "scheduled maintenance",
  breakdown: "a mechanical breakdown",
  driver_unavailable: "the driver was unavailable",
  conductor_unavailable: "the conductor was unavailable",
  permit_suspension: "a permit-related suspension",
  service_cancellation: "the service was cancelled",
  rest_day: "a planned rest day",
  other: "another operational reason",
};

const TRIP_STATUS = {
  completed: { label: "Completed", tone: "ok" },
  cancelled: { label: "Cancelled", tone: "warn" },
  partial: { label: "Stopped early", tone: "warn" },
} as const;

const th = "px-2.5 py-1 text-left text-[0.69rem] font-bold uppercase tracking-[0.07em] text-muted";

function today() {
  return new Date().toLocaleDateString("en-CA"); // yyyy-mm-dd in the browser's own time zone
}

// The Date + Bus Number search (Feature 06): the officer enters the incident date and the bus number, picks the
// right trip if the bus ran more than one, and checks the verified record before using it in a complaint. It
// has exactly these two search inputs. Used on the lookup page and inside the Quick Entry form; what "use"
// does with the chosen record is up to the page that shows it.
export function BusLookupPanel({
  onUse,
  initialDate,
  initialBus = "",
  hint,
}: {
  onUse: (trip: TripDetails) => void;
  initialDate?: string;
  initialBus?: string;
  hint?: string;
}) {
  const [pickedDate, setDate] = useState<string | null>(initialDate || null); // null until changed: then it is today
  const [bus, setBus] = useState(initialBus);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BusSearch | null>(null);
  const [selected, setSelected] = useState<TripDetails | null>(null);
  const [selecting, setSelecting] = useState<number | null>(null);

  // Anything shown belongs to the date and bus that were searched, so a change clears it.
  function edit(change: () => void) {
    change();
    setResult(null);
    setSelected(null);
    setError(null);
  }

  // What went wrong, in the common popup: a session that ended or a missing right is said as such.
  function problem(title: string, status: number | undefined, message: string) {
    if (status === 401 || status === 403) return notify.error("Not allowed", message);
    notify.error(title, message);
  }

  async function choose(id: number, title = "Trip selected") {
    setSelecting(id);
    const found = await loadTrip(id);
    setSelecting(null);
    if (!found.ok) {
      setSelected(null);
      setError(found.message);
      return problem("Could not open that record", found.status, found.message);
    }
    setError(null);
    setSelected(found.data);
    const trip = found.data;
    if (trip.tripStatus === "cancelled") {
      notify.error("This trip was cancelled", `${trip.busNumber}, trip at ${trip.departure}, did not run. Check that the complaint is about the right trip.`);
    } else if (trip.verification === "Verified") {
      notify.success(title, `${trip.busNumber}, trip at ${trip.departure}. The duty details are verified.`);
    } else {
      // Missing or unverified duty information is a problem to see, so it uses the error popup.
      notify.error(
        trip.verification === "Unverified" ? "Duty details are unverified" : "Duty details are unavailable",
        `${trip.busNumber}, trip at ${trip.departure}, is selected, but nobody on duty is named. Nothing is guessed.`,
      );
    }
  }

  async function search(event?: FormEvent) {
    event?.preventDefault();
    const date = pickedDate ?? today();
    if (!date || !bus.trim()) return setError("Enter the incident date and the bus number.");
    setBusy(true);
    setError(null);
    setResult(null);
    setSelected(null);
    const found = await searchTrips(date, bus.trim());
    setBusy(false);
    if (!found.ok) {
      setError(found.message);
      return problem(found.status === 404 ? "Bus not found" : "Could not search", found.status, found.message);
    }
    setResult(found.data);
    const trips = found.data.trips;
    if (trips.length === 0 && found.data.operationStatus === "did_not_operate") {
      const why = REASONS[found.data.nonOperationReason ?? "other"] ?? "an operational reason";
      notify.error("Bus did not operate", `${found.data.vehicle.number} did not operate on ${formatDay(found.data.date)}: ${why}.`);
    } else if (trips.length === 0) {
      notify.error("No matching bus records", `${found.data.vehicle.number} has no published record for ${formatDay(found.data.date)}.`);
    } else if (found.data.operationStatus === "cancelled") {
      notify.error("Cancelled trips only", `Every trip of ${found.data.vehicle.number} on ${formatDay(found.data.date)} was cancelled.`);
    } else if (trips.length === 1) {
      void choose(trips[0].id, "Bus found"); // nothing to choose between
    } else {
      notify.success("Multiple trips available", `${found.data.vehicle.number} ran ${trips.length} trips that day. Select the correct one.`);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={search} className="grid items-end gap-3.5 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
        <Field label="Incident date" htmlFor="lookup-date">
          <input
            id="lookup-date"
            type="date"
            max={today()}
            className={inputClass}
            value={pickedDate ?? today()}
            suppressHydrationWarning
            onChange={(e) => edit(() => setDate(e.target.value))}
          />
        </Field>
        <Field label="Bus number" htmlFor="lookup-bus">
          <input
            id="lookup-bus"
            className={inputClass}
            value={bus}
            placeholder="For example ND-7782"
            autoComplete="off"
            onChange={(e) => edit(() => setBus(e.target.value))}
          />
        </Field>
        <button type="submit" className="sr-only">
          Search
        </button>
        <PillButton primary className="!h-11 !px-6" disabled={busy} onClick={() => void search()}>
          {busy ? "Searching…" : "Search"}
        </PillButton>
      </form>

      {error && <Note tone="alert">{error}</Note>}

      {result && result.trips.length === 0 && result.operationStatus === "did_not_operate" && (
        <Note tone="alert">
          {result.vehicle.number} did not operate on {formatDay(result.date)}:{" "}
          {REASONS[result.nonOperationReason ?? "other"] ?? "an operational reason"}. If the complainant gave this date,
          check it with them. The complaint can be saved as incomplete until the date or the bus is confirmed.
        </Note>
      )}

      {result && result.trips.length === 0 && result.operationStatus !== "did_not_operate" && (
        <Note tone="neutral">
          There is no published record for {result.vehicle.number} on {formatDay(result.date)}, so who drove, who
          conducted and the trip are Unavailable. Nothing is guessed. Permit {result.vehicle.permit ?? "not on record"},
          registered area {result.vehicle.area}. You can still enter the bus by hand and save the complaint as
          incomplete until the record is verified.
        </Note>
      )}

      {result && result.trips.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-separate border-spacing-y-1 text-[0.81rem]">
            <thead>
              <tr>
                <th className={th}>Bus number</th>
                <th className={th}>Permit number</th>
                <th className={th}>Route</th>
                <th className={th}>Departure / trip time</th>
                <th className={th}>Operation status</th>
                <th className={th}>
                  <span className="sr-only">Selection</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {result.trips.map((trip) => {
                const chosen = selected?.id === trip.id;
                return (
                  <tr
                    key={trip.id}
                    className={`*:px-2.5 *:py-2.5 *:first:rounded-l-[1.1rem] *:last:rounded-r-[1.1rem] ${
                      chosen ? "*:bg-crimson/10" : "*:bg-[#faf6f7]"
                    }`}
                  >
                    <td className="font-bold">
                      {trip.busNumber}
                      {trip.synthetic && (
                        <span className="ml-2 align-middle">
                          <Chip tone="info">Simulated</Chip>
                        </span>
                      )}
                    </td>
                    <td className="tabular-nums">{trip.permitNumber}</td>
                    <td>{trip.route}</td>
                    <td className="font-bold tabular-nums">{trip.departure}</td>
                    <td>
                      <Chip tone={TRIP_STATUS[trip.tripStatus].tone}>{TRIP_STATUS[trip.tripStatus].label}</Chip>
                    </td>
                    <td>
                      <div className="flex justify-end">
                        {chosen ? (
                          <Chip tone="brand">Selected</Chip>
                        ) : (
                          <PillButton disabled={selecting !== null} onClick={() => void choose(trip.id)}>
                            {selecting === trip.id ? "Opening…" : "Select"}
                          </PillButton>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {result.trips.length > 1 && !selected && (
            <p className={`mt-2 ${muted}`}>
              This bus ran {result.trips.length} trips that day. Select the one the complaint is about.
            </p>
          )}
        </div>
      )}

      {hint && <p className={muted}>{hint}</p>}
      {selected && <SelectedRecord trip={selected} onUse={() => onUse(selected)} />}
    </div>
  );
}