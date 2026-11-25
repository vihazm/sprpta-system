import { BrandTile } from "@/components/BrandTile";

const STEPS = [
  { label: "Submitted", note: "You lodge the complaint from your portal." },
  { label: "Received", note: "SPRPTA checks it and registers it." },
  { label: "Action in progress", note: "A decision is made and carried out." },
  { label: "Closed", note: "You are told the case is complete." },
];

/** The crimson side of the sign-up page: what happens to a complaint, in the four steps the complainant sees. */
export function SignUpPanel() {
  return (
    <aside className="relative flex flex-col justify-between gap-[2rem] overflow-hidden bg-gradient-to-br from-crimson-deep via-[#A8102F] to-[#cf2a4b] px-[3.2rem] py-[3rem] text-white max-[899px]:px-[1.4rem] max-[899px]:py-[1.6rem]">
      <div
        aria-hidden="true"
        className="absolute -bottom-40 -left-36 size-[30rem] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.2),transparent_68%)]"
      />
      <div className="relative flex items-center gap-[0.7rem]">
        <BrandTile size="2.4rem" />
        <span className="text-[1.05rem] font-extrabold tracking-[0.04em]">SPRPTA</span>
      </div>

      <div className="relative">
        <h1 className="m-0 max-w-[10em] font-display text-[2.9rem] leading-[1.1] tracking-[-0.03em] max-[899px]:text-[2rem]">
          Your complaint, followed to its close.
        </h1>
        <ol className="m-0 mt-[2rem] list-none p-0 max-[899px]:hidden">
          {STEPS.map((step, i) => (
            <li key={step.label} className="flex gap-[1rem]">
              <div className="flex w-[2.1rem] flex-none flex-col items-center">
                <span className="grid size-[2.1rem] place-items-center rounded-full bg-white/15 text-[0.86rem] font-extrabold">
                  {i + 1}
                </span>
                {i < STEPS.length - 1 && <span className="min-h-[2rem] w-[3px] flex-1 rounded-full bg-white/20" />}
              </div>
              <div className="pb-[1.3rem] pt-[0.3rem]">
                <p className="m-0 text-[0.94rem] font-extrabold">{step.label}</p>
                <p className="m-0 mt-[0.2rem] text-[0.82rem] text-white/85">{step.note}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="relative flex flex-col gap-[0.8rem] max-[899px]:hidden">
        <div className="rounded-[1.25rem] border border-white/25 bg-white/10 px-[1.1rem] py-[0.9rem]">
          <p className="m-0 text-[0.7rem] font-bold uppercase tracking-[0.1em] text-[#ffc2cd]">Updates</p>
          <p className="m-0 mt-[0.25rem] text-[0.88rem] font-bold">Sent to you by SMS or email at every step.</p>
        </div>
        <p className="m-0 text-[0.78rem] text-white/80">Bus and trishaw services in Galle, Matara and Hambantota.</p>
      </div>
    </aside>
  );
}
