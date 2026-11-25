import { BrandTile } from "@/components/BrandTile";

const STEPS = [
  { label: "Submitted", note: "You lodge the complaint from your portal." },
  { label: "Received", note: "SPRPTA checks it and registers it." },
  { label: "Action in progress", note: "A decision is made and carried out." },
  { label: "Closed", note: "You are told the case is complete." },
];

/** The crimson half of the sign-up card: what the system promises, and the four steps a complaint goes through. */
export function SignUpPanel() {
  return (
    <section className="relative flex flex-col justify-between gap-[1.8rem] overflow-hidden bg-gradient-to-br from-crimson-deep via-[#A8102F] to-[#cf2a4b] px-[2.7rem] py-[2.7rem] text-white max-[899px]:gap-[1rem] max-[899px]:px-[1.5rem] max-[899px]:py-[1.5rem]">
      <div
        aria-hidden="true"
        className="absolute -right-32 -top-32 size-[22rem] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.22),transparent_65%)]"
      />

      <div className="relative flex items-center gap-[0.7rem]">
        <span className="flex size-[2.6rem] flex-none items-center justify-center rounded-[0.8rem] bg-white">
          <BrandTile size="1.9rem" />
        </span>
        <div className="leading-[1.2]">
          <p className="m-0 text-[1.1rem] font-extrabold tracking-[0.04em]">SPRPTA</p>
          <p className="m-0 text-[0.76rem] text-white/80 max-[599px]:hidden">Complaint &amp; Recommendation System</p>
        </div>
      </div>

      <div className="relative">
        <h1 className="m-0 font-display text-[2.7rem] leading-[1.08] tracking-[-0.03em] max-[899px]:text-[1.9rem]">
          Your complaint, followed to its close.
        </h1>
        <p className="mb-0 mt-[0.9rem] max-w-[23em] text-[0.92rem] leading-[1.55] text-white/90 max-[899px]:hidden">
          Report a problem with a bus or trishaw service and see every step until it is resolved.
        </p>
      </div>

      <ol className="relative m-0 list-none p-0 max-[899px]:hidden">
        {STEPS.map((step, i) => (
          <li key={step.label} className="flex gap-[0.9rem]">
            <div className="flex w-[1.9rem] flex-none flex-col items-center">
              <span className="grid size-[1.9rem] place-items-center rounded-full border border-white/45 bg-white/20 text-[0.8rem] font-extrabold">
                {i + 1}
              </span>
              {i < STEPS.length - 1 && <span className="min-h-[1.3rem] w-[2px] flex-1 bg-white/30" />}
            </div>
            <div className={i < STEPS.length - 1 ? "pb-[0.9rem] pt-[0.15rem]" : "pt-[0.15rem]"}>
              <p className="m-0 text-[0.9rem] font-extrabold">{step.label}</p>
              <p className="m-0 mt-[0.1rem] text-[0.78rem] text-white/82">{step.note}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
