// Glass "bento" tiles shown on the login photo: what the system is for, in words that
// fit every user (passengers, office staff, officers and administrators).
// Both rows add up to 6 columns, so the tiles fill the full width with even edges.

const TILE =
  "rounded-[1.25rem] border border-white/20 bg-white/10 px-[1.25rem] py-[1.1rem] shadow-[0_8px_24px_-12px_rgba(0,0,0,0.5)] backdrop-blur-md";
const TAG = "m-0 text-[0.7rem] font-bold uppercase tracking-[0.1em] text-[#ffb6c3]";
const TITLE = "m-0 mt-[0.3rem] font-extrabold leading-[1.15] tracking-[-0.01em] text-white";
const TEXT = "m-0 mt-[0.4rem] text-[0.86rem] font-medium leading-[1.45] text-white/80";

export function BenefitsBento({ className = "" }: { className?: string }) {
  return (
    <ul className={`m-0 grid list-none grid-cols-6 gap-[0.75rem] p-0 ${className}`}>
      <li className={`${TILE} col-span-4 bg-gradient-to-br from-white/20 to-white/5`}>
        <p className={TAG}>Fairness</p>
        <h3 className={`${TITLE} text-[1.4rem]`}>Fairer public service</h3>
        <p className={TEXT}>
          One clear process for every complaint, handled the same way for everyone.
        </p>
      </li>
      <li className={`${TILE} col-span-2`}>
        <p className={TAG}>Tracking</p>
        <h3 className={`${TITLE} text-[1.1rem]`}>Every step recorded</h3>
        <p className={TEXT}>From first report to closure.</p>
      </li>
      <li className={`${TILE} col-span-2`}>
        <p className={TAG}>Deadlines</p>
        <h3 className={`${TITLE} text-[1.1rem]`}>Clear time targets</h3>
        <p className={TEXT}>So no case is left waiting.</p>
      </li>
      <li className={`${TILE} col-span-4`}>
        <p className={TAG}>Accountability</p>
        <h3 className={`${TITLE} text-[1.2rem]`}>Decisions on the record</h3>
        <p className={TEXT}>
          Actions and their reasons are kept, so outcomes can always be explained and reviewed.
        </p>
      </li>
    </ul>
  );
}
