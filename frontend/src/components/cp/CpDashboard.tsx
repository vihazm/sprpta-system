import Link from "next/link";
import { Card, CardHeading, Chip, LinkButton, bigNumber, eyebrow, muted } from "@/components/dashboard/ui";
import { formatToday } from "@/components/dashboard/dates";
import { getSession } from "@/lib/session";
import { Icon } from "@/components/dashboard/icons";
import { fileUrl, loadComplaints } from "./api";
import { isImage } from "./files";
import { StepBar } from "./StepBar";
import { formatDate, referenceText, statusTone, whatNext } from "./status";
import type { PortalComplaint } from "./types";

const RECENT = 5;

const TIPS = [
  "Give the vehicle number and the route. It helps staff find the right vehicle quickly.",
  "Write the date and place, and what exactly happened.",
  "Describe one problem in each complaint, so each one can be handled on its own.",
];

// The complainant's landing page (UI-CP-03): where their complaints stand, and a way to lodge a new one.
export async function CpDashboard() {
  const [user, result] = await Promise.all([getSession(), loadComplaints()]);
  if (!user) return null; // the shell has already redirected unauthenticated visitors

  const complaints = result.ok ? result.data : [];
  const inProgress = complaints.filter((c) => c.outcome === "open").length;
  const latest = complaints[0];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className={eyebrow}>{formatToday(new Date())}</p>
        <h1 className="mt-1.5 font-display text-[2.4rem] leading-[1.08] tracking-[-0.035em] max-[599px]:text-[1.9rem]">
          Welcome back, {user.name.split(" ")[0]}
        </h1>
      </div>

      {!result.ok && (
        <Card>
          <p className="text-[0.9rem] font-bold text-error">Your complaints could not be loaded.</p>
          <p className={muted}>{result.message}</p>
        </Card>
      )}

      {result.ok && complaints.length === 0 && <FirstComplaint />}

      {latest && <LatestUpdate complaint={latest} />}

      {complaints.length > 0 && (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(13rem,1fr))] gap-5">
          <Card>
            <p className={eyebrow}>Total complaints</p>
            <p className={`${bigNumber} text-[3.4rem]`}>{complaints.length}</p>
          </Card>
          <Card>
            <p className={eyebrow}>In progress</p>
            <p className={`${bigNumber} text-[3.4rem] text-crimson`}>{inProgress}</p>
          </Card>
          <section className="flex flex-col justify-between gap-3.5 rounded-[1.75rem] bg-gradient-to-br from-crimson-deep via-[#A8102F] to-[#cf2a4b] p-6 text-white shadow-[0_30px_50px_-34px_rgba(110,8,30,0.8)]">
            <p className="font-display text-[1.3rem] leading-[1.2]">Something to report?</p>
            <Link
              href="/cp/new-complaint"
              className="focus-ring inline-flex h-11 items-center justify-center rounded-[0.95rem] bg-white text-[0.9rem] font-extrabold text-ink transition-colors hover:bg-field"
            >
              New complaint
            </Link>
          </section>
        </div>
      )}

      <div className="flex flex-wrap items-stretch gap-5">
        {complaints.length > 0 && (
          <Card className="flex-[1.7_1_26rem]">
            <CardHeading
              title="Recent complaints"
              action={<LinkButton href="/cp/complaints">See all</LinkButton>}
            />
            <ul className="m-0 flex list-none flex-col p-0">
              {complaints.slice(0, RECENT).map((c) => (
                <li key={c.id} className="border-t border-[#efe9eb]">
                  <Link
                    href={`/cp/complaints?id=${c.id}`}
                    className="focus-ring flex items-center gap-3.5 rounded-lg px-1 py-3.5 transition-colors hover:bg-[#faf7f8]"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block text-[0.9rem] font-bold">{c.subject}</span>
                      <span className={`block ${muted}`}>
                        {referenceText(c)} · {formatDate(c.submittedAt)}
                        {c.attachments.length > 0 && ` · ${c.attachments.length} ${c.attachments.length === 1 ? "file" : "files"}`}
                      </span>
                    </span>
                    <Chip tone={statusTone(c)}>{c.statusLabel}</Chip>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        )}
        <Card className="flex-[1_1_18rem]">
          <CardHeading title="Tips for a strong complaint" />
          <ul className="m-0 flex list-none flex-col gap-3.5 p-0">
            {TIPS.map((tip, i) => (
              <li key={tip} className="flex items-start gap-[0.7rem]">
                <span className="grid size-6 flex-none place-items-center rounded-lg bg-[#fbeff2] text-[0.75rem] font-extrabold text-crimson">
                  {i + 1}
                </span>
                <span className="text-[0.84rem] leading-[1.45] text-slate-ink">{tip}</span>
              </li>
            ))}
          </ul>
          <p className={`border-t border-[#efe9eb] pt-3 ${muted}`}>Updates about your complaints reach you by SMS or email.</p>
        </Card>
      </div>
    </div>
  );
}

function FirstComplaint() {
  return (
    <Card className="items-start gap-3 !p-8">
      <p className={eyebrow}>Get started</p>
      <h2 className="font-display text-[1.7rem] leading-[1.15]">You have not lodged a complaint yet</h2>
      <p className="max-w-[30rem] text-[0.9rem] leading-[1.5] text-muted">
        If a bus or trishaw service let you down, tell SPRPTA. You can follow every step here once it is submitted.
      </p>
      <Link
        href="/cp/new-complaint"
        className="focus-ring mt-1 inline-flex h-12 items-center rounded-[0.95rem] bg-crimson px-6 text-[0.9rem] font-extrabold text-white transition-colors hover:bg-crimson-hover"
      >
        Lodge your first complaint
      </Link>
    </Card>
  );
}

function LatestUpdate({ complaint }: { complaint: PortalComplaint }) {
  const next = whatNext(complaint);
  return (
    <Card className="!flex-row flex-wrap items-center !gap-x-5 !gap-y-4 !px-6 !py-[1.1rem]">
      <div className="min-w-[17rem] flex-[1_1_17rem]">
        <p className="text-[0.69rem] font-bold uppercase tracking-[0.09em] text-crimson">
          Latest update · {referenceText(complaint)}
        </p>
        <p className="mt-1 text-[0.95rem] font-extrabold">{complaint.subject}</p>
        <p className={`mt-0.5 ${muted}`}>
          {next.title}
          {complaint.attachments.length > 0 &&
            ` · ${complaint.attachments.length} ${complaint.attachments.length === 1 ? "file" : "files"} added`}
        </p>
      </div>
      <StepBar complaint={complaint} className="min-w-40 flex-[1_1_12rem]" />
      <Chip tone={statusTone(complaint)}>{complaint.statusLabel}</Chip>
      <Link
        href={`/cp/complaints?id=${complaint.id}`}
        className="focus-ring inline-flex h-[2.6rem] items-center rounded-[0.9rem] bg-field px-5 text-[0.85rem] font-bold text-slate-ink transition-colors hover:bg-[#e7e8eb]"
      >
        View
      </Link>
      {complaint.attachments.length > 0 && (
        <ul className="m-0 flex w-full list-none flex-wrap gap-2.5 border-t border-[#efe9eb] p-0 pt-3.5" aria-label="Files you added">
          {complaint.attachments.slice(0, 6).map((a) => (
            <li key={a.id}>
              <a
                href={fileUrl(complaint.id, a.id)}
                target="_blank"
                rel="noopener"
                aria-label={`Open ${a.fileName}`}
                title={a.fileName}
                className="focus-ring grid size-[5.2rem] place-items-center overflow-hidden rounded-[1rem] bg-[#f7f4f5] text-crimson"
              >
                {isImage(a.mimeType) ? (
                  // eslint-disable-next-line @next/next/no-img-element -- the person's own upload, served by the API
                  <img src={fileUrl(complaint.id, a.id)} alt="" loading="lazy" className="size-full object-cover" />
                ) : (
                  <Icon name="file" size={26} />
                )}
              </a>
            </li>
          ))}
          {complaint.attachments.length > 6 && (
            <li className="grid size-[5.2rem] place-items-center rounded-[1rem] bg-[#f7f4f5] text-[0.8rem] font-bold text-muted">
              +{complaint.attachments.length - 6}
            </li>
          )}
        </ul>
      )}
    </Card>
  );
}
