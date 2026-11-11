import { bigNumber, muted } from "./ui";

// One figure with a label and a small note, on a soft tile.
export function StatBox({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-[1.1rem] bg-[#f7f4f5] p-[0.9rem]">
      <p className={`${muted} font-bold`}>{label}</p>
      <p className={`${bigNumber} mt-1.5 text-[2.1rem]`}>{value}</p>
      <p className={`${muted} mt-1`}>{note}</p>
    </div>
  );
}
