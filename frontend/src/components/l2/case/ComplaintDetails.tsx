import { Icon } from "@/components/dashboard/icons";
import { Card, CardHeading, Chip } from "@/components/dashboard/ui";
import { attachmentUrl } from "../api";
import { BUS_CHECK_LABEL, fileSize, shortDate } from "../format";
import type { CaseDetail } from "../types";

const LINK_LABEL = { not_duplicate: "Not a duplicate", related: "Related", duplicate_of: "Duplicate of" } as const;

// Everything Level 1 recorded about the complaint. Level 2 sees whether a contact exists, not the contact itself.
export function ComplaintDetails({ c }: { c: CaseDetail }) {
  const facts = [
    { label: "Complainant", value: c.isAnonymous ? "Anonymous" : c.complainant },
    { label: "Contact on record", value: c.hasContact ? "Yes, messages can be sent" : "None" },
    { label: "Complainant is a", value: c.complainantType && c.complainantType.replace(/^\w/, (l) => l.toUpperCase()) },
    { label: "Medium", value: c.medium },
    { label: "Date", value: shortDate(c.complaintDate) },
    { label: "Time of incident", value: c.incidentTime?.slice(0, 5) },
    { label: "Place", value: c.incidentLocation },
    { label: "Vehicle", value: [c.vehicle, c.vehicleType].filter(Boolean).join(" · ") },
    { label: "Permit", value: c.permit },
    { label: "Owner", value: c.owner },
    { label: "Route or stand", value: c.routeStand },
    { label: "Bus check by Level 1", value: c.busVerification && (BUS_CHECK_LABEL[c.busVerification] ?? c.busVerification) },
    { label: "Driver on duty", value: c.driverOnDuty },
    { label: "Conductor on duty", value: c.conductorOnDuty },
    { label: "Complaint against", value: c.target },
    { label: "Accused person", value: c.accused },
    { label: "Category", value: c.category },
  ];

  return (
    <Card>
      <CardHeading title="Complaint details" subtitle="As recorded by Level 1" />
      <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3 rounded-[1.25rem] bg-[#f7f4f5] p-4 sm:grid-cols-4">
        {facts.map((f) => (
          <div key={f.label}>
            <dt className="text-[0.69rem] font-bold text-muted">{f.label}</dt>
            <dd className="m-0 mt-0.5 text-[0.81rem] font-extrabold">{f.value || "–"}</dd>
          </div>
        ))}
      </dl>

      <p className="whitespace-pre-line text-[0.86rem] leading-[1.6]">
        <b className="font-extrabold">What happened.</b> {c.description ?? "No description."}
      </p>

      {c.attachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {c.attachments.map((file) => (
            <a
              key={file.id}
              href={attachmentUrl(c.id, file.id)}
              target="_blank"
              rel="noopener"
              className="focus-ring inline-flex items-center gap-1.5 rounded-[0.65rem] border border-[#ecd2d8] px-2.5 py-1 text-[0.75rem] font-bold text-slate-600 transition-colors hover:border-crimson hover:text-crimson"
            >
              <Icon name="attach" size={13} />
              {file.name} · {fileSize(file.size)}
            </a>
          ))}
        </div>
      )}

      {c.duplicates.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-[0.69rem] font-bold uppercase tracking-[0.09em] text-muted">Level 1&apos;s duplicate check</p>
          <div className="flex flex-wrap gap-2">
            {c.duplicates.map((d) => (
              <Chip key={`${d.reference}-${d.link}`} tone={d.link === "related" ? "warn" : "info"}>
                {d.reference ?? "Earlier case"}: {LINK_LABEL[d.link]}
              </Chip>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
