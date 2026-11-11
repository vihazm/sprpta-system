export type BarItem = {
  label: string;
  value: number;
  share: number; // how full the bar is, 0 to 100
  color?: string; // a CSS colour, defaults to the crimson of the portal
};

// Labelled horizontal bars with the figure on the right.
export function BarRows({
  items,
  labelWidth = "6rem",
  unit = "",
  gap = "gap-[0.6rem]",
}: {
  items: BarItem[];
  labelWidth?: string;
  unit?: string; // shown after each figure, for example "%"
  gap?: string;
}) {
  return (
    <ul className={`m-0 flex list-none flex-col p-0 ${gap}`}>
      {items.map((item) => (
        <li
          key={item.label}
          className="grid items-center gap-2.5 text-[0.78rem] font-bold"
          style={{ gridTemplateColumns: `${labelWidth} minmax(0,1fr) 2.4rem` }}
        >
          <span>{item.label}</span>
          <div className="h-2 overflow-hidden rounded-full bg-[#ece4e7]">
            <div
              className="h-full rounded-full bg-crimson"
              style={{ width: `${item.share}%`, background: item.color }}
            />
          </div>
          <b className="text-right font-extrabold tabular-nums">
            {item.value}
            {unit}
          </b>
        </li>
      ))}
    </ul>
  );
}
